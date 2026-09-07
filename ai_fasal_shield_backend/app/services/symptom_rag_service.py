from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, replace
from typing import Protocol

import httpx
import numpy as np
from app.config import get_settings
from app.constants.symptoms import (
    SUPPORTED_RAG_LANGUAGES,
    SYMPTOM_CONCEPTS,
    SYMPTOM_DICTIONARY_VERSION,
    SymptomCode,
    SymptomConcept,
)
from app.models.schemas import Assessment, ReportLanguage, SymptomMappingItem


logger = logging.getLogger(__name__)


class EmbeddingBackend(Protocol):
    def encode_queries(self, texts: list[str], *, language: str) -> np.ndarray:
        """Return a 2D float array of L2-normalized query embeddings."""

    def encode_documents(self, texts: list[str], *, language: str) -> np.ndarray:
        """Return a 2D float array of L2-normalized concept embeddings."""


class CandidateReranker(Protocol):
    def choose(
        self,
        symptom_span: str,
        *,
        language: str,
        candidates: list["RetrievedCandidate"],
    ) -> "RerankDecision":
        """Score retrieved candidates and return a constrained final decision."""


def _l2_normalize(matrix: np.ndarray) -> np.ndarray:
    if matrix.size == 0:
        return matrix.astype(np.float32)
    matrix = matrix.astype(np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return matrix / norms


_QUERY_INSTRUCTION = (
    "Given a farmer-observed crop symptom, retrieve the canonical agricultural "
    "symptom description that expresses the same observable condition. Match "
    "the symptom meaning itself and do not infer a disease diagnosis."
)


class OllamaEmbeddingBackend:
    """Local multilingual embeddings through Ollama's /api/embed endpoint."""

    def __init__(
        self,
        model_name: str,
        base_url: str,
        timeout_seconds: float = 120.0,
    ) -> None:
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 1), dtype=np.float32)

        try:
            response = httpx.post(
                f"{self.base_url}/api/embed",
                json={
                    "model": self.model_name,
                    "input": texts,
                    "truncate": True,
                    "keep_alive": "10m",
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            embeddings = response.json().get("embeddings")
            if not embeddings or len(embeddings) != len(texts):
                raise ValueError(
                    f"Expected {len(texts)} embeddings, got "
                    f"{0 if not embeddings else len(embeddings)}"
                )
        except Exception as exc:
            raise RuntimeError(
                f"Ollama embedding failed for model {self.model_name!r}: {exc}. "
                f"Make sure Ollama is running and run: ollama pull {self.model_name}"
            ) from exc

        return _l2_normalize(np.asarray(embeddings, dtype=np.float32))

    def encode_queries(self, texts: list[str], *, language: str) -> np.ndarray:
        del language
        instructed = [f"Instruct: {_QUERY_INSTRUCTION}\nQuery: {text}" for text in texts]
        return self._embed(instructed)

    def encode_documents(self, texts: list[str], *, language: str) -> np.ndarray:
        del language
        return self._embed(texts)


class HuggingFaceE5EmbeddingBackend:
    """Optional lightweight benchmark backend for multilingual-e5-small."""

    def __init__(self, model_name: str, device: str = "cpu") -> None:
        self.model_name = model_name
        self.device = device
        self._tokenizer = None
        self._model = None

    def _load(self) -> None:
        if self._model is not None:
            return
        from transformers import AutoModel, AutoTokenizer

        self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self._model = AutoModel.from_pretrained(self.model_name)
        self._model.to(self.device)
        self._model.eval()
        logger.info("Loaded benchmark embedding model %s on %s", self.model_name, self.device)

    def _embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 1), dtype=np.float32)
        self._load()
        import torch

        assert self._tokenizer is not None
        assert self._model is not None
        batch = self._tokenizer(
            texts,
            max_length=256,
            padding=True,
            truncation=True,
            return_tensors="pt",
        )
        batch = {k: v.to(self.device) for k, v in batch.items()}
        with torch.no_grad():
            outputs = self._model(**batch)
            token_embeddings = outputs.last_hidden_state
            attention_mask = batch["attention_mask"].unsqueeze(-1)
            summed = (token_embeddings * attention_mask).sum(dim=1)
            counts = attention_mask.sum(dim=1).clamp(min=1)
            pooled = summed / counts
        return _l2_normalize(pooled.cpu().numpy())

    def encode_queries(self, texts: list[str], *, language: str) -> np.ndarray:
        del language
        return self._embed([f"query: {text}" for text in texts])

    def encode_documents(self, texts: list[str], *, language: str) -> np.ndarray:
        del language
        return self._embed([f"passage: {text}" for text in texts])


@dataclass(frozen=True)
class RetrievedCandidate:
    code: SymptomCode
    name: str
    description: str
    plant_part: str | None
    score: float
    retrieval_language: str
    identity_score: float | None = None
    definition_score: float | None = None
    reranker_score: float | None = None


@dataclass(frozen=True)
class RerankDecision:
    code: SymptomCode
    candidate_scores: dict[SymptomCode, float]
    selected_score: float | None
    second_score: float | None
    margin: float | None
    accepted: bool
    reason: str


class Qwen3DedicatedReranker:
    """Official Qwen3-Reranker-0.6B used locally as a cross-encoder.

    The model is loaded lazily from the Hugging Face cache or downloaded on first
    use. It scores each (farmer symptom, candidate concept) pair with Qwen's
    official yes/no logit method. The generative qwen3:1.7b model is not used here.
    """

    _INSTRUCTION = (
        "Given a farmer-observed crop symptom and a canonical agricultural symptom "
        "description, determine whether the description expresses the same observable "
        "condition. Match the literal symptom meaning itself. Do not infer a disease "
        "diagnosis, cause, or related but different symptom."
    )
    _PREFIX = (
        '<|im_start|>system\nJudge whether the Document meets the requirements based on '
        'the Query and the Instruct provided. Note that the answer can only be "yes" '
        'or "no".<|im_end|>\n<|im_start|>user\n'
    )
    _SUFFIX = '<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n'

    def __init__(
        self,
        *,
        model_name: str,
        device: str = "auto",
        max_length: int = 512,
        min_score: float = 0.50,
        min_margin: float = 0.00,
        local_files_only: bool = False,
    ) -> None:
        self.model_name = model_name
        self.device_setting = device
        self.max_length = max_length
        self.min_score = min_score
        self.min_margin = min_margin
        self.local_files_only = local_files_only
        self._tokenizer = None
        self._model = None
        self._torch = None
        self._device = None
        self._token_true_id = None
        self._token_false_id = None
        self._prefix_tokens: list[int] | None = None
        self._suffix_tokens: list[int] | None = None
        self._load_lock = threading.Lock()
        self._infer_lock = threading.Lock()

    def _resolve_device(self, torch_module) -> str:
        requested = (self.device_setting or "auto").strip().lower()
        if requested == "auto":
            return "cuda" if torch_module.cuda.is_available() else "cpu"
        if requested.startswith("cuda") and not torch_module.cuda.is_available():
            logger.warning("CUDA requested for reranker but unavailable; falling back to CPU")
            return "cpu"
        return requested

    def _load(self) -> None:
        if self._model is not None:
            return
        with self._load_lock:
            if self._model is not None:
                return
            try:
                import torch
                from transformers import AutoModelForCausalLM, AutoTokenizer
            except Exception as exc:
                raise RuntimeError(
                    "Dedicated Qwen reranker dependencies are unavailable. "
                    "Run: pip install -r requirements.txt"
                ) from exc

            device = self._resolve_device(torch)
            dtype = torch.float16 if device.startswith("cuda") else torch.float32
            try:
                tokenizer = AutoTokenizer.from_pretrained(
                    self.model_name,
                    padding_side="left",
                    local_files_only=self.local_files_only,
                )
                if tokenizer.pad_token_id is None:
                    tokenizer.pad_token = tokenizer.eos_token
                model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    torch_dtype=dtype,
                    local_files_only=self.local_files_only,
                )
                model.to(device)
                model.eval()
            except Exception as exc:
                mode = "local cache only" if self.local_files_only else "Hugging Face/cache"
                raise RuntimeError(
                    f"Could not load {self.model_name!r} from {mode}: {exc}. "
                    "Run: python -m scripts.prepare_qwen_reranker"
                ) from exc

            token_true_ids = tokenizer("yes", add_special_tokens=False).input_ids
            token_false_ids = tokenizer("no", add_special_tokens=False).input_ids
            if not token_true_ids or not token_false_ids:
                raise RuntimeError("Qwen reranker tokenizer could not resolve yes/no tokens")

            self._torch = torch
            self._device = device
            self._tokenizer = tokenizer
            self._model = model
            self._token_true_id = token_true_ids[0]
            self._token_false_id = token_false_ids[0]
            self._prefix_tokens = tokenizer.encode(self._PREFIX, add_special_tokens=False)
            self._suffix_tokens = tokenizer.encode(self._SUFFIX, add_special_tokens=False)
            logger.info("Loaded dedicated symptom reranker %s on %s", self.model_name, device)

    @property
    def loaded(self) -> bool:
        return self._model is not None

    @property
    def resolved_device(self) -> str:
        if self._device is not None:
            return self._device
        try:
            import torch
            return self._resolve_device(torch)
        except Exception:
            return self.device_setting

    def cache_status(self) -> str:
        try:
            from huggingface_hub import try_to_load_from_cache
            cached = try_to_load_from_cache(self.model_name, "config.json")
            return "cached" if isinstance(cached, str) else "download_needed"
        except Exception:
            return "unknown"

    @staticmethod
    def _format_pair(instruction: str, query: str, document: str) -> str:
        return f"<Instruct>: {instruction}\n<Query>: {query}\n<Document>: {document}"

    def _score_pairs(self, query: str, documents: list[str]) -> list[float]:
        if not documents:
            return []
        self._load()
        assert self._torch is not None
        assert self._tokenizer is not None
        assert self._model is not None
        assert self._prefix_tokens is not None
        assert self._suffix_tokens is not None
        assert self._token_true_id is not None
        assert self._token_false_id is not None

        pairs = [self._format_pair(self._INSTRUCTION, query, doc) for doc in documents]
        content_max = self.max_length - len(self._prefix_tokens) - len(self._suffix_tokens)
        if content_max < 32:
            raise RuntimeError("SYMPTOM_RERANKER_MAX_LENGTH is too small")

        encoded = self._tokenizer(
            pairs,
            padding=False,
            truncation="longest_first",
            return_attention_mask=False,
            max_length=content_max,
        )
        for i, ids in enumerate(encoded["input_ids"]):
            encoded["input_ids"][i] = self._prefix_tokens + ids + self._suffix_tokens
        batch = self._tokenizer.pad(
            encoded, padding=True, return_tensors="pt", max_length=self.max_length
        )
        batch = {key: value.to(self._device) for key, value in batch.items()}

        with self._infer_lock, self._torch.no_grad():
            logits = self._model(**batch).logits[:, -1, :]
            true_vector = logits[:, self._token_true_id]
            false_vector = logits[:, self._token_false_id]
            binary = self._torch.stack([false_vector, true_vector], dim=1)
            probabilities = self._torch.softmax(binary.float(), dim=1)[:, 1]
        return [float(value) for value in probabilities.detach().cpu().tolist()]

    def warmup(self) -> dict:
        scores = self._score_pairs(
            "پتے مڑ رہے نیں",
            ["پتے مڑ، لپٹ یا بل کھا رہے نیں۔", "پتے پیلے یا زرد ہو رہے نیں۔"],
        )
        return {
            "model": self.model_name,
            "device": self.resolved_device,
            "scores": scores,
            "ready": len(scores) == 2,
        }

    def choose(
        self,
        symptom_span: str,
        *,
        language: str,
        candidates: list[RetrievedCandidate],
    ) -> RerankDecision:
        del language
        if not candidates:
            return RerankDecision(
                code=SymptomCode.OTHERS_MAP,
                candidate_scores={},
                selected_score=None,
                second_score=None,
                margin=None,
                accepted=False,
                reason="no_candidates",
            )

        scores = self._score_pairs(symptom_span, [c.description for c in candidates])
        score_map = {candidate.code: score for candidate, score in zip(candidates, scores)}
        ranked = sorted(score_map.items(), key=lambda item: item[1], reverse=True)
        best_code, best_score = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else None
        margin = best_score - second_score if second_score is not None else None

        if best_score < self.min_score:
            return RerankDecision(
                code=SymptomCode.OTHERS_MAP,
                candidate_scores=score_map,
                selected_score=best_score,
                second_score=second_score,
                margin=margin,
                accepted=False,
                reason="below_reranker_score",
            )
        if second_score is not None and margin is not None and margin < self.min_margin:
            return RerankDecision(
                code=SymptomCode.OTHERS_MAP,
                candidate_scores=score_map,
                selected_score=best_score,
                second_score=second_score,
                margin=margin,
                accepted=False,
                reason="below_reranker_margin",
            )

        return RerankDecision(
            code=best_code,
            candidate_scores=score_map,
            selected_score=best_score,
            second_score=second_score,
            margin=margin,
            accepted=True,
            reason="matched_dedicated_reranker",
        )


class SymptomRAGService:
    """V17 retrieve -> dedicated Qwen3 reranker symptom normalization.

    Responsibilities are intentionally separated:
      * crop + affected part = deterministic metadata filters
      * Qwen3-Embedding-0.6B = candidate retrieval only
      * clear high-score/high-margin retrievals may be accepted directly
      * ambiguous retrievals = Qwen3-Reranker-0.6B cross-encoder scoring
      * qwen3:1.7b remains only for farmer-answer extraction
      * no runtime translation and no symptom alias table
    """

    def __init__(
        self,
        embedder: EmbeddingBackend | None = None,
        reranker: CandidateReranker | None = None,
    ) -> None:
        self.settings = get_settings()
        if embedder is not None:
            self.embedder = embedder
        elif self.settings.symptom_embedding_backend == "ollama":
            self.embedder = OllamaEmbeddingBackend(
                model_name=self.settings.symptom_embedding_model,
                base_url=self.settings.qwen_base_url,
                timeout_seconds=self.settings.symptom_embedding_timeout_seconds,
            )
        elif self.settings.symptom_embedding_backend == "hf_e5":
            self.embedder = HuggingFaceE5EmbeddingBackend(
                model_name=self.settings.symptom_embedding_model,
                device=self.settings.symptom_embedding_device,
            )
        else:
            raise ValueError(
                "SYMPTOM_EMBEDDING_BACKEND must be 'ollama' or 'hf_e5', got "
                f"{self.settings.symptom_embedding_backend!r}"
            )

        if reranker is not None:
            self.reranker = reranker
        else:
            self.reranker = Qwen3DedicatedReranker(
                model_name=self.settings.symptom_reranker_model,
                device=self.settings.symptom_reranker_device,
                max_length=self.settings.symptom_reranker_max_length,
                min_score=self.settings.symptom_reranker_min_score,
                min_margin=self.settings.symptom_reranker_min_margin,
                local_files_only=self.settings.symptom_reranker_local_files_only,
            )

        self._concept_cache: dict[
            tuple[str, str], tuple[list[SymptomConcept], np.ndarray]
        ] = {}

    @staticmethod
    def _normalize_language(language: str | ReportLanguage) -> str:
        if isinstance(language, ReportLanguage):
            value = language.value
        else:
            value = str(language).strip().lower()
        aliases = {
            "en": "english",
            "ur": "urdu",
            "pa": "punjabi",
            "shahmukhi": "punjabi",
            "punjabi_shahmukhi": "punjabi",
        }
        value = aliases.get(value, value)
        if value not in SUPPORTED_RAG_LANGUAGES:
            raise ValueError(
                f"Unsupported RAG language {language!r}. "
                f"Use one of: {', '.join(SUPPORTED_RAG_LANGUAGES)}"
            )
        return value

    def _concepts_for_crop(self, crop: str) -> list[SymptomConcept]:
        return [concept for concept in SYMPTOM_CONCEPTS.values() if crop in concept.crops]

    def _concept_matrix(
        self,
        crop: str,
        language: str | ReportLanguage,
    ) -> tuple[list[SymptomConcept], np.ndarray]:
        language_value = self._normalize_language(language)
        key = (crop, language_value)
        cached = self._concept_cache.get(key)
        if cached is not None:
            return cached

        concepts = self._concepts_for_crop(crop)
        documents = [c.semantic_text_for(language_value) for c in concepts]
        semantic_matrix = self.embedder.encode_documents(documents, language=language_value)
        cached_value = (concepts, semantic_matrix)
        self._concept_cache[key] = cached_value
        return cached_value

    def warmup(
        self,
        *,
        languages: tuple[str, ...] = SUPPORTED_RAG_LANGUAGES,
        crops: tuple[str, ...] = ("cotton", "rice"),
    ) -> None:
        for language in languages:
            for crop in crops:
                self._concept_matrix(crop, language)

    def _eligible_concepts_and_matrix(
        self,
        *,
        crop: str,
        affected_part: str | None,
        language: str | ReportLanguage,
    ) -> tuple[list[SymptomConcept], np.ndarray]:
        concepts, semantic_matrix = self._concept_matrix(crop, language)
        if not concepts:
            return [], semantic_matrix

        if affected_part and " and " not in affected_part:
            indexes = [
                i for i, concept in enumerate(concepts) if concept.plant_part == affected_part
            ]
            if indexes:
                concepts = [concepts[i] for i in indexes]
                semantic_matrix = semantic_matrix[indexes]
        return concepts, semantic_matrix

    def eligible_concepts(self, *, crop: str, affected_part: str | None) -> list[SymptomConcept]:
        concepts = self._concepts_for_crop(crop)
        if affected_part and " and " not in affected_part:
            filtered = [c for c in concepts if c.plant_part == affected_part]
            if filtered:
                concepts = filtered
        return concepts

    @staticmethod
    def build_query_text(
        symptom_span: str,
        *,
        crop: str,
        affected_part: str | None,
    ) -> str:
        del crop, affected_part
        return " ".join((symptom_span or "").strip().split())

    def retrieve(
        self,
        symptom_span: str,
        *,
        crop: str,
        affected_part: str | None,
        language: str | ReportLanguage,
        top_k: int | None = None,
    ) -> list[RetrievedCandidate]:
        language_value = self._normalize_language(language)
        top_k = top_k or self.settings.symptom_rag_top_k
        concepts, semantic_matrix = self._eligible_concepts_and_matrix(
            crop=crop,
            affected_part=affected_part,
            language=language_value,
        )
        if not concepts:
            return []

        query_text = self.build_query_text(
            symptom_span,
            crop=crop,
            affected_part=affected_part,
        )
        if not query_text:
            return []

        query = self.embedder.encode_queries([query_text], language=language_value)[0]
        scores = semantic_matrix @ query
        order = np.argsort(scores)[::-1][:top_k]
        return [
            RetrievedCandidate(
                code=concepts[i].code,
                name=concepts[i].name,
                description=concepts[i].semantic_text_for(language_value),
                plant_part=concepts[i].plant_part,
                score=float(scores[i]),
                retrieval_language=language_value,
                definition_score=float(scores[i]),
            )
            for i in order
        ]

    def _mapping(
        self,
        *,
        symptom_span: str,
        language_value: str,
        code: SymptomCode,
        status: str,
        candidates: list[RetrievedCandidate],
        rerank_decision: RerankDecision | None = None,
    ) -> SymptomMappingItem:
        best_score = candidates[0].score if candidates else 0.0
        if code == SymptomCode.OTHERS_MAP:
            selected_score = best_score
            comparison_scores = [c.score for c in candidates[1:]]
        else:
            selected = next((c for c in candidates if c.code == code), None)
            selected_score = selected.score if selected is not None else best_score
            comparison_scores = [c.score for c in candidates if c.code != code]
        second_score = max(comparison_scores) if comparison_scores else None
        margin = selected_score - second_score if second_score is not None else None
        concept_name = None if code == SymptomCode.OTHERS_MAP else SYMPTOM_CONCEPTS[code].name
        return SymptomMappingItem(
            symptom=symptom_span,
            retrieval_language=ReportLanguage(language_value),
            code=code,
            concept_name=concept_name,
            similarity=selected_score,
            second_best_similarity=second_score,
            margin=margin,
            reranker_score=(rerank_decision.selected_score if rerank_decision else None),
            reranker_second_score=(rerank_decision.second_score if rerank_decision else None),
            reranker_margin=(rerank_decision.margin if rerank_decision else None),
            reranker_reason=(rerank_decision.reason if rerank_decision else None),
            status=status,
        )

    def map_one(
        self,
        symptom_span: str,
        *,
        crop: str,
        affected_part: str | None,
        language: str | ReportLanguage,
        use_reranker: bool | None = None,
        top_k: int | None = None,
    ) -> tuple[SymptomCode, SymptomMappingItem, list[RetrievedCandidate]]:
        language_value = self._normalize_language(language)
        top_k = top_k or self.settings.symptom_rerank_top_k
        candidates = self.retrieve(
            symptom_span,
            crop=crop,
            affected_part=affected_part,
            language=language_value,
            top_k=top_k,
        )
        if not candidates:
            return (
                SymptomCode.OTHERS_MAP,
                self._mapping(
                    symptom_span=symptom_span,
                    language_value=language_value,
                    code=SymptomCode.OTHERS_MAP,
                    status="below_threshold",
                    candidates=[],
                ),
                [],
            )

        best = candidates[0]
        second_score = candidates[1].score if len(candidates) > 1 else None
        margin = best.score - second_score if second_score is not None else 1.0

        # A very weak retrieval does not deserve an LLM rescue. Fail safe.
        # This floor is intentionally lower than the direct-accept gate because
        # retrieval and final classification are now separate responsibilities.
        if best.score < self.settings.symptom_retrieval_floor:
            return (
                SymptomCode.OTHERS_MAP,
                self._mapping(
                    symptom_span=symptom_span,
                    language_value=language_value,
                    code=SymptomCode.OTHERS_MAP,
                    status="below_threshold",
                    candidates=candidates,
                ),
                candidates,
            )

        # High confidence + clear separation can be accepted directly.
        direct_accept = (
            best.score >= self.settings.symptom_direct_accept_threshold
            and margin >= self.settings.symptom_direct_accept_margin
        )
        if direct_accept:
            return (
                best.code,
                self._mapping(
                    symptom_span=symptom_span,
                    language_value=language_value,
                    code=best.code,
                    status="matched_semantic",
                    candidates=candidates,
                ),
                candidates,
            )

        # V17.1 fix: parent/child relationships are NOT sufficient to bypass
        # the dedicated reranker. Any result that misses the strong direct
        # accept gate above must be reranked when reranking is enabled.

        if use_reranker is None:
            use_reranker = self.settings.symptom_rerank_enabled
        if not use_reranker:
            return (
                SymptomCode.OTHERS_MAP,
                self._mapping(
                    symptom_span=symptom_span,
                    language_value=language_value,
                    code=SymptomCode.OTHERS_MAP,
                    status="ambiguous",
                    candidates=candidates,
                ),
                candidates,
            )

        rerank_candidates = candidates[: self.settings.symptom_rerank_top_k]
        try:
            decision = self.reranker.choose(
                symptom_span,
                language=language_value,
                candidates=rerank_candidates,
            )
            candidates = [
                replace(c, reranker_score=decision.candidate_scores.get(c.code))
                for c in candidates
            ]
        except Exception as exc:
            logger.exception("Dedicated symptom rerank failed: %s", exc)
            return (
                SymptomCode.OTHERS_MAP,
                self._mapping(
                    symptom_span=symptom_span,
                    language_value=language_value,
                    code=SymptomCode.OTHERS_MAP,
                    status="rerank_failed",
                    candidates=candidates,
                ),
                candidates,
            )

        selected = decision.code
        if selected == SymptomCode.OTHERS_MAP:
            return (
                selected,
                self._mapping(
                    symptom_span=symptom_span,
                    language_value=language_value,
                    code=selected,
                    status="reranked_other",
                    candidates=candidates,
                    rerank_decision=decision,
                ),
                candidates,
            )

        candidate_codes = {c.code for c in rerank_candidates}
        if selected not in candidate_codes:
            logger.error("Dedicated reranker returned non-retrieved code %s", selected.value)
            selected = SymptomCode.OTHERS_MAP
            status = "rerank_failed"
        else:
            status = "matched_reranked"

        return (
            selected,
            self._mapping(
                symptom_span=symptom_span,
                language_value=language_value,
                code=selected,
                status=status,
                candidates=candidates,
                rerank_decision=decision,
            ),
            candidates,
        )

    def debug_map_one(
        self,
        symptom_span: str,
        *,
        crop: str,
        affected_part: str | None,
        language: str | ReportLanguage,
        use_reranker: bool = True,
        top_k: int = 5,
    ) -> dict:
        code, mapping, candidates = self.map_one(
            symptom_span,
            crop=crop,
            affected_part=affected_part,
            language=language,
            use_reranker=use_reranker,
            top_k=top_k,
        )
        second = candidates[1].score if len(candidates) > 1 else None
        margin = candidates[0].score - second if candidates and second is not None else None
        language_value = self._normalize_language(language)
        reranker_used = mapping.status in {"matched_reranked", "reranked_other", "rerank_failed"}
        return {
            "symptom": symptom_span,
            "language": language_value,
            "crop": crop,
            "affected_part": affected_part,
            "embedding_model": self.settings.symptom_embedding_model,
            "reranker_model": self.settings.symptom_reranker_model,
            "reranker_device": getattr(self.reranker, "resolved_device", self.settings.symptom_reranker_device),
            "dictionary_version": SYMPTOM_DICTIONARY_VERSION,
            "use_reranker": use_reranker,
            "reranker_used": reranker_used,
            "reranker_mode": "qwen3_reranker_0.6b_cross_encoder",
            "reranker_top_score": mapping.reranker_score,
            "reranker_second_score": mapping.reranker_second_score,
            "reranker_margin": mapping.reranker_margin,
            "reranker_reason": mapping.reranker_reason,
            "decision_stage": "dedicated_reranker" if reranker_used else "embedding_direct",
            "candidates": [
                {
                    "rank": i + 1,
                    "code": c.code.value,
                    "name": c.name,
                    "description": c.description,
                    "score": c.score,
                    "reranker_score": c.reranker_score,
                }
                for i, c in enumerate(candidates)
            ],
            "top_score": candidates[0].score if candidates else None,
            "second_score": second,
            "margin": margin,
            "final_code": code.value,
            "status": mapping.status,
            "concept_name": mapping.concept_name,
        }

    def enrich_assessment(
        self,
        assessment: Assessment,
        *,
        crop: str,
        language: str | ReportLanguage,
    ) -> Assessment:
        language_value = self._normalize_language(language)
        raw_spans = [s for s in assessment.symptoms if s and s.strip()]
        codes: list[SymptomCode] = []
        mappings: list[SymptomMappingItem] = []
        display_symptoms: list[str] = []

        for span in raw_spans:
            code, mapping, candidates = self.map_one(
                span,
                crop=crop,
                affected_part=assessment.affected_part,
                language=language_value,
            )
            mappings.append(mapping)
            if code not in codes:
                codes.append(code)
            display = span if code == SymptomCode.OTHERS_MAP else SYMPTOM_CONCEPTS[code].name.lower()
            if display not in display_symptoms:
                display_symptoms.append(display)

            logger.warning(
                "[SYMPTOM] lang=%s text=%r final=%s embed=%.3f margin=%s "
                "reranker_used=%s rerank_score=%s status=%s top=%s",
                language_value,
                span,
                code.value,
                mapping.similarity,
                "n/a" if mapping.margin is None else f"{mapping.margin:.3f}",
                mapping.status in {"matched_reranked", "reranked_other", "rerank_failed"},
                "n/a" if mapping.reranker_score is None else f"{mapping.reranker_score:.3f}",
                mapping.status,
                [(c.code.value, round(c.score, 3)) for c in candidates],
            )

        assessment.symptoms = display_symptoms
        assessment.symptom_codes = codes
        assessment.symptom_mapping = mappings
        assessment.symptom_dictionary_version = SYMPTOM_DICTIONARY_VERSION
        return assessment
