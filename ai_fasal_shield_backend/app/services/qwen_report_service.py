import json
import logging
import re

import httpx
from pydantic import BaseModel, Field

from app.config import get_settings
from app.constants.plant_parts import (
    contains_explicit_plant_part,
    explicit_plant_part_mentions,
)
from app.models.schemas import Assessment, FarmerInput


logger = logging.getLogger(__name__)


Q1_PROMPT = r"""
You are a strict evidence-preserving extraction assistant for AI Fasal Shield.

You receive ONE farmer answer to:
"What problem or changes do you see in the crop?"

The answer may be Urdu, Punjabi/Shahmukhi, mixed Urdu-Punjabi, or English.

Your job is NOT to translate or normalize the symptom wording.
Your job is only to identify distinct observable symptom phrases in the ORIGINAL answer.

For `symptom_spans`:
- COPY symptom phrases exactly from the farmer answer.
- Each returned span must be a contiguous substring of the original answer.
- Never translate, paraphrase, replace, correct, or explain the farmer's words.
- Separate EVERY distinct explicitly stated observable change into its own span when possible.
- Punjabi/Shahmukhi conjunctions such as "تے" and Urdu "اور" can join separate observations; split them when each side describes a distinct visible change.
- Do not diagnose a disease.
- Do not invent a symptom.
- Do not include duration, field area, or spread information.

Example:
answer: "پتے پیلے ہو رہے ہیں اور مڑ رہے ہیں"
valid symptom_spans: ["پتے پیلے ہو رہے ہیں", "مڑ رہے ہیں"]
INVALID: ["leaf yellowing", "leaf curling"] because those are translations.

For `affected_part`:
- Return a concise English plant-part label ONLY when the answer explicitly mentions it.
- Allowed values: leaves, stem, roots, boll, panicle, grain, whole plant.
- Recognize explicit Urdu/Punjabi plant-part words even though symptom spans stay verbatim.
  Examples: پتے/پتیاں -> leaves, تنا -> stem, جڑیں/جڑاں -> roots,
  ٹینڈا/ٹینڈے/ٹینڈیاں -> boll, بالی/بالیاں -> panicle,
  دانہ/دانے -> grain, پودا/بوٹا -> whole plant.
- This plant-part normalization does NOT change the symptom wording.
- Never infer a plant part from a symptom.
- If no plant part is explicit, return null.

Return only JSON matching the supplied schema.
"""


Q2_PROMPT = """
You receive ONE farmer answer to:
"When did you first notice this problem?"

The answer may be Urdu, Punjabi/Shahmukhi, mixed Urdu-Punjabi, or English.
Understand it internally and return only `problem_duration` in concise English.

Normalize clear durations:
- three days ago -> "3 days"
- one week ago -> "1 week"
- two months ago -> "2 months"

If the answer genuinely does not provide a duration/onset, return null.
Never invent a duration. Return only JSON matching the supplied schema.
"""


Q3_PROMPT = """
You receive ONE farmer answer to:
"How much of your field or how many plants are affected?"

The answer may be Urdu, Punjabi/Shahmukhi, mixed Urdu-Punjabi, or English.
Understand it internally and return only `affected_area` in concise English.

The value may be area or number of plants.
Normalize clear quantities and units:
- half an acre -> "0.5 acre"
- two kanal -> "2 kanal"
- fifty plants -> "50 plants"

If the answer genuinely does not provide affected extent, return null.
Never invent or calculate missing information. Return only JSON matching the supplied schema.
"""


Q4_PROMPT = """
You receive ONE farmer answer to:
"Is the problem spreading or getting worse?"

The answer may be Urdu, Punjabi/Shahmukhi, mixed Urdu-Punjabi, or English.
Understand it internally and return only `spread_status` in concise English.

Prefer values such as:
- "spreading"
- "not spreading"
- "stable"
- "getting worse"
- "improving"

Do not infer worsening just because something is spreading.
If the answer genuinely does not provide spread/change information, return null.
Never invent information. Return only JSON matching the supplied schema.
"""


class Q1Result(BaseModel):
    symptom_spans: list[str] = Field(default_factory=list)
    affected_part: str | None = None


class Q2Result(BaseModel):
    problem_duration: str | None = None


class Q3Result(BaseModel):
    affected_area: str | None = None


class Q4Result(BaseModel):
    spread_status: str | None = None


class QwenUnavailable(RuntimeError):
    pass


class QwenReportService:
    def __init__(self) -> None:
        self.settings = get_settings()

    @staticmethod
    def fallback() -> Assessment:
        return Assessment()

    @staticmethod
    def _has_answer(value: str | None) -> bool:
        # Short answers such as "yes", "no", "2 days" are valid.
        return bool(value and value.strip())

    @staticmethod
    def _clean_json_content(content: str) -> str:
        text = (content or "").strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text)
        text = text.strip()
        if not text:
            raise ValueError("Qwen returned empty content")
        return text

    @staticmethod
    def _normalize_space(text: str) -> str:
        return " ".join((text or "").strip().split())

    @classmethod
    def _propagate_shared_plant_part_context(cls, raw: str, spans: list[str]) -> list[str]:
        """Carry an explicitly shared plant-part subject into later fragments.

        Farmers often state the subject once and then coordinate symptoms:
        ``پتے پیلے ہو رہے ہیں اور مڑ رہے ہیں``. A syntax split produces
        ``پتے پیلے ہو رہے ہیں`` + ``مڑ رہے ہیں``; the latter is semantically
        weak on its own. If the complete answer contains exactly one explicit
        plant part, prepend the exact farmer term to fragments that omit it.

        This is context restoration, not symptom translation or alias mapping.
        If more than one plant part is explicitly present, nothing is propagated.
        """
        mentions = explicit_plant_part_mentions(raw)
        if len(mentions) != 1:
            return spans

        _, raw_term = mentions[0]
        enriched: list[str] = []
        for span in spans:
            span_norm = cls._normalize_space(span)
            if not span_norm:
                continue
            if contains_explicit_plant_part(span_norm):
                enriched_span = span_norm
            else:
                enriched_span = cls._normalize_space(f"{raw_term} {span_norm}")
            if enriched_span not in enriched:
                enriched.append(enriched_span)
        return enriched

    @classmethod
    def _fallback_split_raw_q1(cls, raw: str) -> list[str]:
        """Conservative syntax-only fallback for multi-symptom Q1 answers.

        This is not symptom alias mapping. It only separates common explicit
        conjunctions so the semantic retriever can evaluate each observation,
        then restores a single shared plant-part subject when one is explicit.
        """
        cleaned = cls._normalize_space(raw)
        if not cleaned:
            return []

        # Syntax-only split for common English/Urdu/Punjabi conjunctions.
        # This does not map symptom meaning; it only preserves multiple explicit
        # observations as separate evidence spans for the semantic pipeline.
        parts = re.split(r"\s+(?:اور|تے|and)\s+", cleaned, flags=re.IGNORECASE)
        parts = [p.strip(" ,.;،؛") for p in parts if p.strip(" ,.;،؛")]
        if 1 < len(parts) <= 4:
            return cls._propagate_shared_plant_part_context(raw, parts)
        return [cleaned]

    @classmethod
    def _validated_original_spans(cls, raw: str, spans: list[str]) -> list[str]:
        """Accept only evidence copied from the original farmer answer.

        If Qwen translates/paraphrases instead of copying, reject the output and
        fall back to the raw answer (split only by explicit conjunctions).
        """
        raw_norm = cls._normalize_space(raw)
        if not raw_norm:
            return []

        validated: list[str] = []
        for span in spans:
            span_norm = cls._normalize_space(span)
            if not span_norm:
                continue
            if span_norm not in raw_norm:
                logger.warning(
                    "Rejected non-verbatim Q1 span %r because it is not in raw answer %r",
                    span,
                    raw,
                )
                return cls._fallback_split_raw_q1(raw)
            if span_norm not in validated:
                validated.append(span_norm)

        if not validated:
            return cls._fallback_split_raw_q1(raw)

        # If Qwen returned the complete sentence as one span, split only on an
        # explicit conjunction so multiple symptoms are not lost.
        if len(validated) == 1 and validated[0] == raw_norm:
            return cls._fallback_split_raw_q1(raw)

        return cls._propagate_shared_plant_part_context(raw, validated)

    def _call_qwen(
        self,
        *,
        stage: str,
        system_prompt: str,
        payload: dict,
        response_model: type[BaseModel],
        num_predict: int = 180,
    ) -> BaseModel:
        request_json = {
            "model": self.settings.qwen_model,
            "stream": False,
            "format": response_model.model_json_schema(),
            "think": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(payload, ensure_ascii=False),
                },
            ],
            "options": {
                "temperature": 0.0,
                "num_ctx": 2048,
                "num_predict": num_predict,
            },
            "keep_alive": "10m",
        }

        try:
            response = httpx.post(
                f"{self.settings.qwen_base_url.rstrip('/')}/api/chat",
                json=request_json,
                timeout=self.settings.qwen_timeout_seconds,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            body = ""
            if getattr(exc, "response", None) is not None:
                body = exc.response.text[:1000]
            raise QwenUnavailable(
                f"{stage} request to Ollama failed: {exc}. Response: {body}"
            ) from exc

        try:
            body = response.json()
            content = (body.get("message") or {}).get("content", "")
            cleaned = self._clean_json_content(content)
            result = response_model.model_validate_json(cleaned)
        except Exception as exc:
            raise QwenUnavailable(
                f"{stage} returned invalid structured output: {exc}. "
                f"Raw response={response.text[:1500]!r}"
            ) from exc

        logger.warning("%s output: %s", stage, result.model_dump(mode="json"))
        return result

    def generate(self, farmer: FarmerInput) -> Assessment:
        """Process each available farmer answer independently.

        Q1 is evidence-preserving: Qwen only copies original symptom spans. The
        spans stay in the farmer's original language. When one explicit plant
        part is shared across coordinated symptoms, Python restores that subject
        on later fragments before multilingual semantic retrieval. Q2-Q4 stay normalized to concise English.

        Missing answers are skipped and become []/None.
        """
        assessment = Assessment()

        if self._has_answer(farmer.symptoms_raw):
            q1 = self._call_qwen(
                stage="Q1 verbatim symptom spans",
                system_prompt=Q1_PROMPT,
                payload={
                    "question": "What problem or changes do you see in the crop?",
                    "answer": farmer.symptoms_raw,
                },
                response_model=Q1Result,
                num_predict=180,
            )
            assert isinstance(q1, Q1Result)
            assessment.symptoms = self._validated_original_spans(
                farmer.symptoms_raw,
                q1.symptom_spans,
            )
            assessment.affected_part = q1.affected_part

        if self._has_answer(farmer.onset_raw):
            q2 = self._call_qwen(
                stage="Q2 duration",
                system_prompt=Q2_PROMPT,
                payload={
                    "question": "When did you first notice this problem?",
                    "answer": farmer.onset_raw,
                },
                response_model=Q2Result,
            )
            assert isinstance(q2, Q2Result)
            assessment.problem_duration = q2.problem_duration

        if self._has_answer(farmer.affected_extent_raw):
            q3 = self._call_qwen(
                stage="Q3 affected extent",
                system_prompt=Q3_PROMPT,
                payload={
                    "question": "How much of your field or how many plants are affected?",
                    "answer": farmer.affected_extent_raw,
                },
                response_model=Q3Result,
            )
            assert isinstance(q3, Q3Result)
            assessment.affected_area = q3.affected_area

        if self._has_answer(farmer.spread_raw):
            q4 = self._call_qwen(
                stage="Q4 spread",
                system_prompt=Q4_PROMPT,
                payload={
                    "question": "Is the problem spreading or getting worse?",
                    "answer": farmer.spread_raw,
                },
                response_model=Q4Result,
            )
            assert isinstance(q4, Q4Result)
            assessment.spread_status = q4.spread_status

        return assessment
