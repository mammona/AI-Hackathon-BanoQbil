from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.constants.symptoms import SymptomCode
from app.models.schemas import CropName, ReportLanguage
from app.services.symptom_rag_service import Qwen3DedicatedReranker, SymptomRAGService


router = APIRouter(prefix="/rag", tags=["Symptom RAG Test"])
service = SymptomRAGService()
DATASET = Path(__file__).resolve().parents[2] / "evaluation" / "punjabi_rag_10_reports.json"


class RAGTestRequest(BaseModel):
    symptom: str = Field(min_length=1)
    crop: CropName
    language: ReportLanguage
    affected_part: str | None = None
    use_reranker: bool = True
    top_k: int = Field(default=5, ge=2, le=10)


class RAGCandidateResponse(BaseModel):
    rank: int
    code: str
    name: str
    description: str
    score: float
    reranker_score: float | None = None


class RAGTestResponse(BaseModel):
    symptom: str
    language: str
    crop: str
    affected_part: str | None
    embedding_model: str
    reranker_model: str
    reranker_device: str
    dictionary_version: str
    use_reranker: bool
    reranker_used: bool
    reranker_mode: str
    reranker_top_score: float | None = None
    reranker_second_score: float | None = None
    reranker_margin: float | None = None
    reranker_reason: str | None = None
    decision_stage: str
    candidates: list[RAGCandidateResponse]
    top_score: float | None
    second_score: float | None
    margin: float | None
    final_code: str
    status: str
    concept_name: str | None


class SuiteCaseResult(BaseModel):
    report_id: str
    symptom: str
    expected_code: str
    predicted_code: str
    top1_code: str | None
    expected_in_top3: bool
    expected_in_top5: bool
    status: str
    passed: bool
    candidates: list[RAGCandidateResponse]


class SuiteMetrics(BaseModel):
    total_symptoms: int
    known_symptoms: int
    unknown_symptoms: int
    top1_correct: int
    top3_recall: int
    top5_recall: int
    final_correct: int
    final_accuracy: float


class RAGSuiteResponse(BaseModel):
    language: str
    use_reranker: bool
    metrics: SuiteMetrics
    cases: list[SuiteCaseResult]


def _load_dataset() -> list[dict]:
    try:
        return json.loads(DATASET.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not load test dataset: {exc}") from exc


def _run_suite(reports: list[dict], *, use_reranker: bool) -> RAGSuiteResponse:
    results: list[SuiteCaseResult] = []
    known = unknown = top1 = top3 = top5 = final_correct = 0

    for report in reports:
        for item in report["rag_symptoms"]:
            expected = SymptomCode(item["expected_code"])
            try:
                debug = service.debug_map_one(
                    item["text"],
                    crop=report["crop"],
                    affected_part=report["affected_part"],
                    language=report["language"],
                    use_reranker=use_reranker,
                    top_k=5,
                )
            except Exception as exc:
                raise HTTPException(
                    status_code=500,
                    detail=f"RAG suite failed on {report['report_id']}: {exc}",
                ) from exc

            candidate_codes = [c["code"] for c in debug["candidates"]]
            predicted = debug["final_code"]
            is_known = expected != SymptomCode.OTHERS_MAP
            if is_known:
                known += 1
                if candidate_codes and candidate_codes[0] == expected.value:
                    top1 += 1
                if expected.value in candidate_codes[:3]:
                    top3 += 1
                if expected.value in candidate_codes[:5]:
                    top5 += 1
            else:
                unknown += 1

            passed = predicted == expected.value
            if passed:
                final_correct += 1

            results.append(
                SuiteCaseResult(
                    report_id=report["report_id"],
                    symptom=item["text"],
                    expected_code=expected.value,
                    predicted_code=predicted,
                    top1_code=(candidate_codes[0] if candidate_codes else None),
                    expected_in_top3=(expected.value in candidate_codes[:3] if is_known else False),
                    expected_in_top5=(expected.value in candidate_codes[:5] if is_known else False),
                    status=debug["status"],
                    passed=passed,
                    candidates=[RAGCandidateResponse(**c) for c in debug["candidates"]],
                )
            )

    total = len(results)
    return RAGSuiteResponse(
        language="punjabi",
        use_reranker=use_reranker,
        metrics=SuiteMetrics(
            total_symptoms=total,
            known_symptoms=known,
            unknown_symptoms=unknown,
            top1_correct=top1,
            top3_recall=top3,
            top5_recall=top5,
            final_correct=final_correct,
            final_accuracy=(final_correct / total if total else 0.0),
        ),
        cases=results,
    )


@router.get("/health")
def rag_health():
    reranker = service.reranker
    if isinstance(reranker, Qwen3DedicatedReranker):
        return {
            "status": "ready" if reranker.cache_status() == "cached" else "setup_required",
            "embedding_model": service.settings.symptom_embedding_model,
            "reranker_model": reranker.model_name,
            "reranker_cache": reranker.cache_status(),
            "reranker_loaded": reranker.loaded,
            "reranker_device": reranker.resolved_device,
            "reranker_min_score": reranker.min_score,
            "reranker_min_margin": reranker.min_margin,
            "setup_command": "python -m scripts.prepare_qwen_reranker",
        }
    return {"status": "custom_reranker", "reranker": type(reranker).__name__}


@router.post("/reranker/warmup")
def warmup_reranker():
    reranker = service.reranker
    if not isinstance(reranker, Qwen3DedicatedReranker):
        return {"status": "skipped", "reason": "custom reranker injected"}
    try:
        return {"status": "ready", **reranker.warmup()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Reranker warmup failed: {exc}") from exc


@router.post("/test", response_model=RAGTestResponse)
def test_rag(request: RAGTestRequest):
    """Test one symptom directly without image, database, or Q1 extraction."""
    try:
        return service.debug_map_one(
            request.symptom,
            crop=request.crop.value,
            affected_part=request.affected_part,
            language=request.language,
            use_reranker=request.use_reranker,
            top_k=request.top_k,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"RAG test failed: {exc}") from exc


@router.get("/test-suite/punjabi/reports")
def list_punjabi_reports():
    return [
        {
            "report_id": report["report_id"],
            "crop": report["crop"],
            "answer_1": report["answer_1"],
            "symptom_count": len(report["rag_symptoms"]),
        }
        for report in _load_dataset()
    ]


@router.post("/test-suite/punjabi/report/{report_id}", response_model=RAGSuiteResponse)
def test_one_punjabi_report(
    report_id: str,
    use_reranker: bool = Query(default=True),
):
    reports = [r for r in _load_dataset() if r["report_id"] == report_id]
    if not reports:
        raise HTTPException(status_code=404, detail=f"Unknown report_id: {report_id}")
    return _run_suite(reports, use_reranker=use_reranker)


@router.post("/test-suite/punjabi", response_model=RAGSuiteResponse)
def test_punjabi_suite(use_reranker: bool = Query(default=True)):
    """Run the complete 10-report Punjabi/Shahmukhi benchmark."""
    return _run_suite(_load_dataset(), use_reranker=use_reranker)
