"""Run 10 live farmer-language + multilingual symptom-RAG cases.

Requirements:
- Ollama running
- qwen3:1.7b pulled
- qwen3-embedding:0.6b pulled

This script does not run image validation, SigLIP, disease models, or FastAPI.
It isolates the four-question farmer pipeline and semantic symptom mapping.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from app.constants.plant_parts import validate_affected_part
from app.models.schemas import FarmerInput
from app.services.qwen_report_service import QwenReportService
from app.services.symptom_rag_service import SymptomRAGService


@dataclass(frozen=True)
class EvalCase:
    name: str
    crop: str
    language: str
    q1: str
    q2: str
    q3: str
    q4: str
    expected_codes: tuple[str, ...]
    expected_part: str | None
    expected_duration: str | None
    expected_area: str | None
    expected_spread: str | None


CASES = [
    EvalCase(
        "multi_symptom_leaf",
        "cotton",
        "urdu",
        "پتے پیلے ہو رہے ہیں اور مڑ رہے ہیں",
        "تین دن پہلے شروع ہوا",
        "تقریباً آدھا ایکڑ متاثر ہے",
        "ہاں مسئلہ پھیل رہا ہے",
        ("LEAF_YELLOWING", "LEAF_CURLING"),
        "leaves",
        "3 days",
        "0.5 acre",
        "spreading",
    ),
    EvalCase(
        "brown_spots_and_drying",
        "rice",
        "urdu",
        "پتوں پر بھورے دھبے ہیں اور پتے خشک ہو رہے ہیں",
        "ایک ہفتہ پہلے شروع ہوا",
        "تقریباً ایک ایکڑ متاثر ہے",
        "مسئلہ ابھی نہیں پھیل رہا",
        ("LEAF_BROWN_SPOTS", "LEAF_DRYING"),
        "leaves",
        "1 week",
        "1 acre",
        "not spreading",
    ),
    EvalCase(
        "stem_darkening_weakening",
        "cotton",
        "urdu",
        "تنا کالا ہو رہا ہے اور کمزور بھی ہے",
        "پانچ دن پہلے دیکھا",
        "دو کنال متاثر ہیں",
        "مسئلہ آہستہ آہستہ پھیل رہا ہے",
        ("STEM_DARKENING", "STEM_WEAKENING"),
        "stem",
        "5 days",
        "2 kanal",
        "spreading",
    ),
    EvalCase(
        "whole_plant_wilting_pale",
        "cotton",
        "urdu",
        "پودا مرجھا رہا ہے اور رنگ ہلکا ہو گیا ہے",
        "دو دن پہلے شروع ہوا",
        "تقریباً پچاس پودے متاثر ہیں",
        "حالت ابھی ایک جیسی ہے",
        ("PLANT_WILTING", "PLANT_DISCOLORATION"),
        "whole plant",
        "2 days",
        "50 plants",
        "stable",
    ),
    EvalCase(
        "english_rice_spindle_lesion",
        "rice",
        "english",
        "There are spindle-shaped lesions with pointed ends on the leaves.",
        "4 days ago",
        "30 plants are affected",
        "It is spreading",
        ("LEAF_SPINDLE_LESIONS",),
        "leaves",
        "4 days",
        "30 plants",
        "spreading",
    ),
    EvalCase(
        "cotton_boll_rot_and_spots",
        "cotton",
        "urdu",
        "ٹینڈے سڑ رہے ہیں اور ان پر بھورے دھبے بھی ہیں",
        "چھ دن پہلے",
        "ایک کنال متاثر ہے",
        "مسئلہ بڑھ رہا ہے",
        ("BOLL_ROTTING", "BOLL_SPOTS"),
        "boll",
        "6 days",
        "1 kanal",
        "getting worse",
    ),
    EvalCase(
        "missing_q2",
        "rice",
        "urdu",
        "پتوں پر لمبی لکیریں نظر آ رہی ہیں",
        "",
        "بیس پودے متاثر ہیں",
        "حالت ایک جیسی ہے",
        ("LEAF_STREAKS",),
        "leaves",
        None,
        "20 plants",
        "stable",
    ),
    EvalCase(
        "missing_q1",
        "cotton",
        "urdu",
        "",
        "چار دن پہلے شروع ہوا",
        "ایک کنال متاثر ہے",
        "مسئلہ نہیں پھیل رہا",
        (),
        None,
        "4 days",
        "1 kanal",
        "not spreading",
    ),
    EvalCase(
        "unknown_symptom_to_others",
        "cotton",
        "urdu",
        "پتوں پر چپچپا میٹھا مادہ لگا ہوا ہے",
        "دو دن پہلے",
        "دس پودے متاثر ہیں",
        "حالت ایک جیسی ہے",
        ("OTHERS_MAP",),
        "leaves",
        "2 days",
        "10 plants",
        "stable",
    ),
    EvalCase(
        "rice_panicle_drying",
        "rice",
        "urdu",
        "بالیاں وقت سے پہلے خشک ہو رہی ہیں",
        "ایک ہفتہ پہلے",
        "آدھا ایکڑ متاثر ہے",
        "حالت خراب ہو رہی ہے",
        ("PANICLE_DRYING",),
        "panicle",
        "1 week",
        "0.5 acre",
        "getting worse",
    ),
]


def norm(value: str | None) -> str | None:
    if value is None:
        return None
    return " ".join(value.strip().lower().split())


def same_value(actual: str | None, expected: str | None) -> bool:
    return norm(actual) == norm(expected)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=int, help="Run only case number 1-10")
    args = parser.parse_args()

    selected = CASES
    start_index = 1
    if args.case:
        if not 1 <= args.case <= len(CASES):
            raise SystemExit("--case must be between 1 and 10")
        selected = [CASES[args.case - 1]]
        start_index = args.case

    qwen = QwenReportService()
    rag = SymptomRAGService()

    try:
        rag.warmup(languages=("english", "urdu", "punjabi"), crops=("cotton", "rice"))
    except Exception as exc:
        print("Embedding warmup failed:", exc)
        return 2

    passed = 0

    for offset, case in enumerate(selected):
        index = start_index + offset
        print("\n" + "=" * 82)
        print(f"CASE {index}: {case.name} [{case.crop}] language={case.language}")
        print("=" * 82)

        farmer = FarmerInput(
            language=case.language,
            symptoms_raw=case.q1,
            onset_raw=case.q2,
            affected_extent_raw=case.q3,
            spread_raw=case.q4,
        )

        try:
            assessment = qwen.generate(farmer)
            print("Q1 context-preserved original-language spans:", assessment.symptoms)
            assessment.affected_part = validate_affected_part(
                farmer.symptoms_raw,
                assessment.affected_part,
            )
            print("Validated affected part:", assessment.affected_part)
            for raw_span in assessment.symptoms:
                query = rag.build_query_text(
                    raw_span, crop=case.crop, affected_part=assessment.affected_part
                )
                eligible = rag.eligible_concepts(
                    crop=case.crop, affected_part=assessment.affected_part
                )
                candidates = rag.retrieve(
                    raw_span, crop=case.crop, affected_part=assessment.affected_part, language=case.language
                )
                print("  Meaning-only retrieval query:", query.replace("\n", " | "))
                print("  Eligible concepts:", len(eligible))
                for rank, c in enumerate(candidates, 1):
                    print(f"    top{rank}: {c.code.value} similarity={c.score:.4f}")
            assessment = rag.enrich_assessment(assessment, crop=case.crop, language=case.language)
        except Exception as exc:
            print(f"FAIL: pipeline exception: {exc}")
            continue

        actual_codes = tuple(code.value for code in assessment.symptom_codes)
        checks = {
            "codes": set(actual_codes) == set(case.expected_codes),
            "affected_part": same_value(assessment.affected_part, case.expected_part),
            "problem_duration": same_value(assessment.problem_duration, case.expected_duration),
            "affected_area": same_value(assessment.affected_area, case.expected_area),
            "spread_status": same_value(assessment.spread_status, case.expected_spread),
        }

        print("Canonical display symptoms:", assessment.symptoms)
        print("Mapped codes:", list(actual_codes))
        print("Affected part:", assessment.affected_part)
        print("Duration:", assessment.problem_duration)
        print("Affected extent:", assessment.affected_area)
        print("Spread:", assessment.spread_status)
        print("Mapping details:")
        for item in assessment.symptom_mapping:
            margin = "n/a" if item.margin is None else f"{item.margin:.3f}"
            print(
                f"  - raw={item.symptom!r} -> {item.code.value} "
                f"score={item.similarity:.3f} margin={margin} "
                f"status={item.status}"
            )

        print("Checks:")
        for key, ok in checks.items():
            print(f"  {'PASS' if ok else 'FAIL'} {key}")

        case_ok = all(checks.values())
        print("CASE RESULT:", "PASS" if case_ok else "FAIL")
        passed += int(case_ok)

    print("\n" + "=" * 82)
    print(f"FINAL: {passed}/{len(selected)} cases passed")
    print("=" * 82)
    return 0 if passed == len(selected) else 1


if __name__ == "__main__":
    raise SystemExit(main())
