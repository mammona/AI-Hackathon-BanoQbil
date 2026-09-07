"""RAG-only evaluation on 10 realistic Punjabi/Shahmukhi farmer reports.

IMPORTANT: this script deliberately bypasses Qwen extraction and the final API.
It tests ONLY the current symptom retrieval/mapping layer so we can determine
whether retrieval is good enough before adding any reranker or changing runtime
logic.

It can A/B test the current Qwen3-Embedding query instruction against a plain
query with no instruction, without changing production code.

Usage:
  python scripts/evaluate_punjabi_rag_reports.py
  python scripts/evaluate_punjabi_rag_reports.py --mode current
  python scripts/evaluate_punjabi_rag_reports.py --mode plain
  python scripts/evaluate_punjabi_rag_reports.py --mode both --case RAG-PB-001
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

# When this file is run directly as:
#   python scripts/evaluate_punjabi_rag_reports.py
# Python puts the scripts/ folder on sys.path, not the project root.
# Add the backend root before importing the app package.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.constants.symptoms import SYMPTOM_CONCEPTS, SymptomCode
from app.services.symptom_rag_service import (
    OllamaEmbeddingBackend,
    SymptomRAGService,
)

DATASET = ROOT / "evaluation" / "punjabi_rag_10_reports.json"


class PlainQueryOllamaEmbeddingBackend(OllamaEmbeddingBackend):
    """A/B benchmark backend: same model/docs, but no query instruction."""

    def encode_queries(self, texts: list[str], *, language: str):
        del language
        return self._embed(texts)


@dataclass
class Metrics:
    known: int = 0
    unknown: int = 0
    top1_correct: int = 0
    top3_contains_expected: int = 0
    top5_contains_expected: int = 0
    final_correct: int = 0
    ambiguous: int = 0
    below_threshold: int = 0
    matched: int = 0

    def update(
        self,
        *,
        expected: SymptomCode,
        predicted: SymptomCode,
        candidate_codes: list[SymptomCode],
        status: str,
    ) -> None:
        if expected == SymptomCode.OTHERS_MAP:
            self.unknown += 1
        else:
            self.known += 1
            if candidate_codes and candidate_codes[0] == expected:
                self.top1_correct += 1
            if expected in candidate_codes[:3]:
                self.top3_contains_expected += 1
            if expected in candidate_codes[:5]:
                self.top5_contains_expected += 1

        if predicted == expected:
            self.final_correct += 1
        if status == "ambiguous":
            self.ambiguous += 1
        elif status == "below_threshold":
            self.below_threshold += 1
        elif status.startswith("matched"):
            self.matched += 1


def _load_reports() -> list[dict]:
    reports = json.loads(DATASET.read_text(encoding="utf-8"))
    if len(reports) != 10:
        raise RuntimeError(f"Expected exactly 10 reports, found {len(reports)}")
    return reports


def _service(mode: str) -> SymptomRAGService:
    if mode == "current":
        return SymptomRAGService()

    if mode == "plain":
        settings = get_settings()
        if settings.symptom_embedding_backend != "ollama":
            raise RuntimeError(
                "--mode plain currently requires SYMPTOM_EMBEDDING_BACKEND=ollama"
            )
        embedder = PlainQueryOllamaEmbeddingBackend(
            model_name=settings.symptom_embedding_model,
            base_url=settings.qwen_base_url,
            timeout_seconds=settings.symptom_embedding_timeout_seconds,
        )
        return SymptomRAGService(embedder=embedder)

    raise ValueError(mode)


def _pct(n: int, d: int) -> str:
    return "n/a" if d == 0 else f"{100.0 * n / d:.1f}%"


def _print_summary(label: str, metrics: Metrics, total_symptoms: int) -> None:
    print("\n" + "#" * 104)
    print(f"SUMMARY: {label}")
    print(f"  total symptom mappings : {total_symptoms}")
    print(f"  known canonical cases  : {metrics.known}")
    print(f"  unknown/OTHER cases    : {metrics.unknown}")
    print(
        f"  retrieval Top-1       : {metrics.top1_correct}/{metrics.known} "
        f"({_pct(metrics.top1_correct, metrics.known)})"
    )
    print(
        f"  retrieval Top-3 recall: {metrics.top3_contains_expected}/{metrics.known} "
        f"({_pct(metrics.top3_contains_expected, metrics.known)})"
    )
    print(
        f"  retrieval Top-5 recall: {metrics.top5_contains_expected}/{metrics.known} "
        f"({_pct(metrics.top5_contains_expected, metrics.known)})"
    )
    print(
        f"  FINAL decision accuracy: {metrics.final_correct}/{total_symptoms} "
        f"({_pct(metrics.final_correct, total_symptoms)})"
    )
    print(f"  matched               : {metrics.matched}")
    print(f"  ambiguous             : {metrics.ambiguous}")
    print(f"  below threshold       : {metrics.below_threshold}")
    print("#" * 104)


def _run_mode(mode: str, reports: Iterable[dict], *, verbose_docs: bool) -> Metrics:
    service = _service(mode)
    service.warmup(languages=("punjabi",), crops=("cotton", "rice"))
    metrics = Metrics()
    total = 0

    print("\n" + "=" * 104)
    if mode == "current":
        print("MODE=current: production Qwen3-Embedding query instruction is ON")
    else:
        print("MODE=plain: same embedding model and same Punjabi concept docs, query instruction is OFF")
    print("This is RAG-only. Qwen extraction, plant-part extraction, image AI, and API logic are bypassed.")
    print("=" * 104)

    for report in reports:
        print("\n" + "-" * 104)
        print(
            f"{report['report_id']} | crop={report['crop']} | language={report['language']} "
            f"| affected_part={report['affected_part']}"
        )
        print(f"Q1 full report text: {report['answer_1']}")

        for symptom in report["rag_symptoms"]:
            total += 1
            expected = SymptomCode(symptom["expected_code"])
            query = symptom["text"]
            predicted, mapping, candidates = service.map_one(
                query,
                crop=report["crop"],
                affected_part=report["affected_part"],
                language=report["language"],
                use_reranker=False,
                top_k=5,
            )
            candidate_codes = [c.code for c in candidates]
            metrics.update(
                expected=expected,
                predicted=predicted,
                candidate_codes=candidate_codes,
                status=mapping.status,
            )

            if expected == SymptomCode.OTHERS_MAP:
                retrieval_mark = "UNKNOWN"
            elif candidate_codes and candidate_codes[0] == expected:
                retrieval_mark = "TOP1_OK"
            elif expected in candidate_codes[:3]:
                retrieval_mark = "TOP3_OK"
            elif expected in candidate_codes[:5]:
                retrieval_mark = "TOP5_OK"
            else:
                retrieval_mark = "MISSED_TOP5"

            final_mark = "PASS" if predicted == expected else "FAIL"
            print(f"\n  symptom : {query}")
            print(f"  expected: {expected.value}")
            for rank, candidate in enumerate(candidates[:5], 1):
                flag = " <= expected" if candidate.code == expected else ""
                print(
                    f"  top{rank:<2}: {candidate.code.value:<28} score={candidate.score:.4f}{flag}"
                )
                if verbose_docs:
                    print(f"         doc: {candidate.description}")
            print(
                f"  retrieval={retrieval_mark} | final={predicted.value} | "
                f"status={mapping.status} | score={mapping.similarity:.4f} | "
                f"margin={mapping.margin} | {final_mark}"
            )

    _print_summary(mode, metrics, total)
    return metrics


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["current", "plain", "both"], default="both")
    ap.add_argument(
        "--case",
        help="Optional report id, e.g. RAG-PB-001. If omitted all 10 reports are tested.",
    )
    ap.add_argument(
        "--no-docs",
        action="store_true",
        help="Hide the exact Punjabi candidate descriptions to make output shorter.",
    )
    args = ap.parse_args()

    reports = _load_reports()
    if args.case:
        reports = [r for r in reports if r["report_id"] == args.case]
        if not reports:
            raise SystemExit(f"Unknown report id: {args.case}")

    modes = [args.mode] if args.mode != "both" else ["current", "plain"]
    results: dict[str, Metrics] = {}
    for mode in modes:
        results[mode] = _run_mode(mode, reports, verbose_docs=not args.no_docs)

    if len(results) == 2:
        current = results["current"]
        plain = results["plain"]
        print("\n" + "=" * 104)
        print("A/B COMPARISON (do NOT change production yet; use this evidence first)")
        print(
            f"  current Top-1: {current.top1_correct}/{current.known} | "
            f"plain Top-1: {plain.top1_correct}/{plain.known}"
        )
        print(
            f"  current Top-3: {current.top3_contains_expected}/{current.known} | "
            f"plain Top-3: {plain.top3_contains_expected}/{plain.known}"
        )
        print(
            f"  current Top-5: {current.top5_contains_expected}/{current.known} | "
            f"plain Top-5: {plain.top5_contains_expected}/{plain.known}"
        )
        print(
            f"  current final: {current.final_correct} | plain final: {plain.final_correct}"
        )
        print(
            "Interpretation: if correct concepts are frequently in Top-3 but final decisions are ambiguous, "
            "retrieval is suitable for a constrained reranker. If expected concepts are often missing from "
            "Top-3, improve retrieval/model/descriptions before adding a reranker."
        )
        print("=" * 104)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
