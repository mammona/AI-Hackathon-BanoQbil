import numpy as np

from app.constants.symptoms import SymptomCode
from app.services.symptom_rag_service import (
    Qwen3DedicatedReranker,
    RerankDecision,
    RetrievedCandidate,
    SymptomRAGService,
)


class DummyEmbedder:
    def encode_queries(self, texts: list[str], *, language: str) -> np.ndarray:
        del language
        return np.ones((len(texts), 3), dtype=np.float32)

    def encode_documents(self, texts: list[str], *, language: str) -> np.ndarray:
        del language
        return np.ones((len(texts), 3), dtype=np.float32)


class FakeDedicatedReranker:
    def __init__(self, decision: RerankDecision):
        self.decision = decision
        self.calls = 0

    def choose(self, symptom_span, *, language, candidates):
        del symptom_span, language, candidates
        self.calls += 1
        return self.decision


def candidate(code: SymptomCode, score: float) -> RetrievedCandidate:
    return RetrievedCandidate(
        code=code,
        name=code.value,
        description=f"meaning of {code.value}",
        plant_part="leaves",
        score=score,
        retrieval_language="punjabi",
    )


def decision(code, scores, reason="matched_dedicated_reranker"):
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top = ranked[0][1] if ranked else None
    second = ranked[1][1] if len(ranked) > 1 else None
    return RerankDecision(
        code=code,
        candidate_scores=scores,
        selected_score=top,
        second_score=second,
        margin=(top-second if top is not None and second is not None else None),
        accepted=code != SymptomCode.OTHERS_MAP,
        reason=reason,
    )


def test_clear_embedding_match_skips_dedicated_reranker(monkeypatch):
    fake = FakeDedicatedReranker(decision(SymptomCode.LEAF_CURLING, {}))
    service = SymptomRAGService(embedder=DummyEmbedder(), reranker=fake)
    monkeypatch.setattr(
        service,
        "retrieve",
        lambda *a, **k: [
            candidate(SymptomCode.LEAF_YELLOWING, 0.72),
            candidate(SymptomCode.LEAF_DISCOLORATION, 0.54),
            candidate(SymptomCode.LEAF_DRYING, 0.50),
        ],
    )
    code, mapping, _ = service.map_one(
        "پتے پیلے ہو رہے نیں", crop="cotton", affected_part="leaves", language="punjabi"
    )
    assert code == SymptomCode.LEAF_YELLOWING
    assert mapping.status == "matched_semantic"
    assert fake.calls == 0


def test_ambiguous_embedding_can_be_corrected_by_dedicated_reranker(monkeypatch):
    scores = {
        SymptomCode.LEAF_YELLOWING: 0.08,
        SymptomCode.LEAF_DRYING: 0.12,
        SymptomCode.LEAF_CURLING: 0.96,
    }
    fake = FakeDedicatedReranker(decision(SymptomCode.LEAF_CURLING, scores))
    service = SymptomRAGService(embedder=DummyEmbedder(), reranker=fake)
    monkeypatch.setattr(
        service,
        "retrieve",
        lambda *a, **k: [
            candidate(SymptomCode.LEAF_YELLOWING, 0.599),
            candidate(SymptomCode.LEAF_DRYING, 0.569),
            candidate(SymptomCode.LEAF_CURLING, 0.566),
        ],
    )
    code, mapping, candidates = service.map_one(
        "پتے مڑ وی رہے نیں", crop="cotton", affected_part="leaves", language="punjabi"
    )
    assert code == SymptomCode.LEAF_CURLING
    assert mapping.status == "matched_reranked"
    assert mapping.reranker_score == 0.96
    assert next(c for c in candidates if c.code == SymptomCode.LEAF_CURLING).reranker_score == 0.96


def test_unknown_can_be_rejected_by_dedicated_reranker(monkeypatch):
    scores = {
        SymptomCode.LEAF_YELLOWING: 0.12,
        SymptomCode.LEAF_DRYING: 0.11,
        SymptomCode.LEAF_CURLING: 0.09,
    }
    fake = FakeDedicatedReranker(
        decision(SymptomCode.OTHERS_MAP, scores, reason="below_reranker_score")
    )
    service = SymptomRAGService(embedder=DummyEmbedder(), reranker=fake)
    monkeypatch.setattr(
        service,
        "retrieve",
        lambda *a, **k: [
            candidate(SymptomCode.LEAF_YELLOWING, 0.50),
            candidate(SymptomCode.LEAF_DRYING, 0.49),
            candidate(SymptomCode.LEAF_CURLING, 0.48),
        ],
    )
    code, mapping, _ = service.map_one(
        "پتیاں اُتے چپچپا میٹھا مادہ جمیا ہویا اے",
        crop="cotton",
        affected_part="leaves",
        language="punjabi",
    )
    assert code == SymptomCode.OTHERS_MAP
    assert mapping.status == "reranked_other"
    assert mapping.reranker_reason == "below_reranker_score"


def test_real_dedicated_reranker_selects_highest_probability(monkeypatch):
    reranker = Qwen3DedicatedReranker(
        model_name="Qwen/Qwen3-Reranker-0.6B",
        device="cpu",
        min_score=0.50,
        min_margin=0.0,
    )
    monkeypatch.setattr(reranker, "_score_pairs", lambda q, docs: [0.08, 0.11, 0.94])
    candidates = [
        candidate(SymptomCode.LEAF_YELLOWING, 0.599),
        candidate(SymptomCode.LEAF_DRYING, 0.569),
        candidate(SymptomCode.LEAF_CURLING, 0.566),
    ]
    result = reranker.choose("پتے مڑ وی رہے نیں", language="punjabi", candidates=candidates)
    assert result.code == SymptomCode.LEAF_CURLING
    assert result.accepted is True
    assert result.selected_score == 0.94


def test_real_dedicated_reranker_rejects_low_relevance(monkeypatch):
    reranker = Qwen3DedicatedReranker(
        model_name="Qwen/Qwen3-Reranker-0.6B",
        device="cpu",
        min_score=0.50,
        min_margin=0.0,
    )
    monkeypatch.setattr(reranker, "_score_pairs", lambda q, docs: [0.22, 0.18, 0.14])
    result = reranker.choose(
        "unseen symptom",
        language="punjabi",
        candidates=[
            candidate(SymptomCode.LEAF_YELLOWING, 0.50),
            candidate(SymptomCode.LEAF_DRYING, 0.49),
            candidate(SymptomCode.LEAF_CURLING, 0.48),
        ],
    )
    assert result.code == SymptomCode.OTHERS_MAP
    assert result.reason == "below_reranker_score"


def test_reranker_margin_gate_is_optional_and_configurable(monkeypatch):
    reranker = Qwen3DedicatedReranker(
        model_name="Qwen/Qwen3-Reranker-0.6B",
        min_score=0.5,
        min_margin=0.05,
    )
    monkeypatch.setattr(reranker, "_score_pairs", lambda q, docs: [0.80, 0.78])
    result = reranker.choose(
        "query",
        language="punjabi",
        candidates=[
            candidate(SymptomCode.LEAF_DRYING, 0.59),
            candidate(SymptomCode.LEAF_EDGE_DRYING, 0.56),
        ],
    )
    assert result.code == SymptomCode.OTHERS_MAP
    assert result.reason == "below_reranker_margin"


def test_parent_child_small_margin_calls_dedicated_reranker(monkeypatch):
    scores = {
        SymptomCode.LEAF_YELLOWING: 0.97,
        SymptomCode.LEAF_DISCOLORATION: 0.40,
        SymptomCode.LEAF_DRYING: 0.10,
    }
    fake = FakeDedicatedReranker(decision(SymptomCode.LEAF_YELLOWING, scores))
    service = SymptomRAGService(embedder=DummyEmbedder(), reranker=fake)
    monkeypatch.setattr(
        service,
        "retrieve",
        lambda *a, **k: [
            candidate(SymptomCode.LEAF_YELLOWING, 0.6273),
            candidate(SymptomCode.LEAF_DISCOLORATION, 0.5945),
            candidate(SymptomCode.LEAF_DRYING, 0.55),
        ],
    )
    code, mapping, _ = service.map_one(
        "پتیاں دے سرے پیلے ہو رہے نیں",
        crop="cotton",
        affected_part="leaves",
        language="punjabi",
    )
    assert fake.calls == 1
    assert code == SymptomCode.LEAF_YELLOWING
    assert mapping.status == "matched_reranked"
    assert mapping.reranker_score == 0.97
