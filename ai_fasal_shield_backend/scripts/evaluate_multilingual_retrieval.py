"""Evaluate multilingual symptom RAG independently of generative Qwen.

This is the first script to run. It tests whether original Urdu/Punjabi/English
symptom text can retrieve the correct canonical concept directly.

Default backend: local Ollama qwen3-embedding:0.6b.
Optional benchmark: multilingual-e5-small through Hugging Face.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from app.constants.symptoms import SymptomCode
from app.services.symptom_rag_service import (
    HuggingFaceE5EmbeddingBackend,
    OllamaEmbeddingBackend,
    SymptomRAGService,
)
from app.config import get_settings


@dataclass(frozen=True)
class RetrievalCase:
    name: str
    crop: str
    text: str
    affected_part: str | None
    expected: SymptomCode


CASES = [
    RetrievalCase(
        "urdu_leaf_yellowing",
        "cotton",
        "پتے پیلے ہو رہے ہیں",
        "leaves",
        SymptomCode.LEAF_YELLOWING,
    ),
    RetrievalCase(
        "urdu_leaf_curling",
        "cotton",
        "پتے مڑ رہے ہیں",
        "leaves",
        SymptomCode.LEAF_CURLING,
    ),
    RetrievalCase(
        "urdu_brown_leaf_spots",
        "rice",
        "پتوں پر بھورے دھبے ہیں",
        "leaves",
        SymptomCode.LEAF_BROWN_SPOTS,
    ),
    RetrievalCase(
        "urdu_leaf_drying",
        "rice",
        "پتے خشک ہو رہے ہیں",
        "leaves",
        SymptomCode.LEAF_DRYING,
    ),
    RetrievalCase(
        "urdu_stem_darkening",
        "cotton",
        "تنا کالا ہو رہا ہے",
        "stem",
        SymptomCode.STEM_DARKENING,
    ),
    RetrievalCase(
        "urdu_stem_weakening",
        "cotton",
        "تنا کمزور ہو گیا ہے",
        "stem",
        SymptomCode.STEM_WEAKENING,
    ),
    RetrievalCase(
        "urdu_whole_plant_wilting",
        "cotton",
        "پودا مرجھا رہا ہے",
        "whole plant",
        SymptomCode.PLANT_WILTING,
    ),
    RetrievalCase(
        "urdu_cotton_boll_rot",
        "cotton",
        "ٹینڈے سڑ رہے ہیں",
        "boll",
        SymptomCode.BOLL_ROTTING,
    ),
    RetrievalCase(
        "urdu_rice_panicle_drying",
        "rice",
        "بالیاں وقت سے پہلے خشک ہو رہی ہیں",
        "panicle",
        SymptomCode.PANICLE_DRYING,
    ),
    RetrievalCase(
        "unknown_sticky_residue",
        "cotton",
        "پتوں پر چپچپا میٹھا مادہ لگا ہوا ہے",
        "leaves",
        SymptomCode.OTHERS_MAP,
    ),
]


def make_service(backend: str, model: str | None) -> SymptomRAGService:
    settings = get_settings()
    if backend == "ollama":
        embedder = OllamaEmbeddingBackend(
            model_name=model or "qwen3-embedding:0.6b",
            base_url=settings.qwen_base_url,
            timeout_seconds=settings.symptom_embedding_timeout_seconds,
        )
    else:
        embedder = HuggingFaceE5EmbeddingBackend(
            model_name=model or "intfloat/multilingual-e5-small",
            device=settings.symptom_embedding_device,
        )
    return SymptomRAGService(embedder=embedder)


def run_cases(service: SymptomRAGService, selected: list[RetrievalCase]) -> int:
    passed = 0
    print(
        f"Threshold={service.settings.symptom_match_threshold:.3f} | "
        f"minimum margin={service.settings.symptom_min_margin:.3f} | "
        "scoring=meaning-only cosine similarity"
    )

    for idx, case in enumerate(selected, 1):
        print("\n" + "=" * 82)
        print(f"CASE {idx}: {case.name} [{case.crop}] part={case.affected_part}")
        print("Raw query:", case.text)
        structured_query = service.build_query_text(
            case.text, crop=case.crop, affected_part=case.affected_part
        )
        eligible = service.eligible_concepts(
            crop=case.crop, affected_part=case.affected_part
        )
        print("Meaning-only retrieval query:")
        for line in structured_query.splitlines():
            print("  ", line)
        print(f"Eligible concepts after crop/part filtering: {len(eligible)}")

        code, mapping, candidates = service.map_one(
            case.text,
            crop=case.crop,
            affected_part=case.affected_part,
            language="urdu",
        )

        for rank, candidate in enumerate(candidates, 1):
            print(
                f"  top{rank}: {candidate.code.value:<28} "
                f"similarity={candidate.score:.4f} | {candidate.name}"
            )

        ok = code == case.expected
        print(
            f"RESULT: {'PASS' if ok else 'FAIL'} | predicted={code.value} "
            f"expected={case.expected.value} | status={mapping.status} "
            f"margin={mapping.margin}"
        )
        passed += int(ok)

    print("\n" + "=" * 82)
    print(f"FINAL: {passed}/{len(selected)} retrieval cases passed")
    print("=" * 82)
    return passed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=int, help="Run only one case, 1-10")
    parser.add_argument(
        "--backend",
        choices=["ollama", "hf_e5"],
        default="ollama",
    )
    parser.add_argument("--model", help="Override embedding model name")
    args = parser.parse_args()

    selected = CASES
    if args.case:
        if not 1 <= args.case <= len(CASES):
            raise SystemExit("--case must be between 1 and 10")
        selected = [CASES[args.case - 1]]

    service = make_service(args.backend, args.model)
    try:
        service.warmup(languages=("urdu",), crops=("cotton", "rice"))
        passed = run_cases(service, selected)
    except Exception as exc:
        print("\nERROR:", exc)
        return 2

    return 0 if passed == len(selected) else 1


if __name__ == "__main__":
    raise SystemExit(main())
