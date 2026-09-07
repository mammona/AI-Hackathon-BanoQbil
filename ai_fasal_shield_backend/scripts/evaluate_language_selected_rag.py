"""Evaluate V11 language-selected symptom RAG.

Usage:
    python scripts/evaluate_language_selected_rag.py --language urdu
    python scripts/evaluate_language_selected_rag.py --language punjabi
    python scripts/evaluate_language_selected_rag.py --language english

The SAME 10 canonical concepts are tested in each language. No runtime
translation is used. The selected language chooses only that language's concept
embeddings.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from app.constants.symptoms import SymptomCode
from app.services.symptom_rag_service import SymptomRAGService


@dataclass(frozen=True)
class Case:
    name: str
    crop: str
    part: str | None
    expected: SymptomCode
    english: str
    urdu: str
    punjabi: str


CASES = [
    Case(
        "leaf_yellowing",
        "cotton",
        "leaves",
        SymptomCode.LEAF_YELLOWING,
        "the leaves are turning yellow",
        "پتے پیلے ہو رہے ہیں",
        "پتے پیلے ہو رہے نیں",
    ),
    Case(
        "leaf_curling",
        "cotton",
        "leaves",
        SymptomCode.LEAF_CURLING,
        "the leaves are curling and rolling",
        "پتے مڑ رہے ہیں",
        "پتے مڑ رہے نیں",
    ),
    Case(
        "brown_leaf_spots",
        "rice",
        "leaves",
        SymptomCode.LEAF_BROWN_SPOTS,
        "there are separate brown spots on the leaves",
        "پتوں پر بھورے دھبے ہیں",
        "پتیاں اُتے بھورے دھبے نیں",
    ),
    Case(
        "leaf_drying",
        "rice",
        "leaves",
        SymptomCode.LEAF_DRYING,
        "the leaves are becoming dry",
        "پتے خشک ہو رہے ہیں",
        "پتے سک رہے نیں",
    ),
    Case(
        "stem_darkening",
        "cotton",
        "stem",
        SymptomCode.STEM_DARKENING,
        "the stem is turning dark black",
        "تنا کالا ہو رہا ہے",
        "تنا کالا ہو رہیا اے",
    ),
    Case(
        "stem_weakening",
        "cotton",
        "stem",
        SymptomCode.STEM_WEAKENING,
        "the stem has become weak",
        "تنا کمزور ہو گیا ہے",
        "تنا کمزور ہو گیا اے",
    ),
    Case(
        "whole_plant_wilting",
        "cotton",
        "whole plant",
        SymptomCode.PLANT_WILTING,
        "the whole plant is wilting and drooping",
        "پودا مرجھا رہا ہے",
        "پودا مرجھا رہیا اے",
    ),
    Case(
        "cotton_boll_rot",
        "cotton",
        "boll",
        SymptomCode.BOLL_ROTTING,
        "the cotton bolls are rotting",
        "ٹینڈے گل سڑ رہے ہیں",
        "ٹینڈے گل سڑ رہے نیں",
    ),
    Case(
        "rice_panicle_drying",
        "rice",
        "panicle",
        SymptomCode.PANICLE_DRYING,
        "the rice panicles are drying before maturity",
        "بالیاں وقت سے پہلے خشک ہو رہی ہیں",
        "بالیاں وقت توں پہلاں سک رہیاں نیں",
    ),
    Case(
        "unknown_sticky_residue",
        "cotton",
        "leaves",
        SymptomCode.OTHERS_MAP,
        "there is a sticky sweet residue on the leaves",
        "پتوں پر چپچپا میٹھا مادہ لگا ہوا ہے",
        "پتیاں اُتے چپچپا میٹھا مادہ لگیا اے",
    ),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--language",
        required=True,
        choices=["english", "urdu", "punjabi"],
    )
    parser.add_argument("--case", type=int, help="Run only one case, 1-10")
    args = parser.parse_args()

    selected = CASES
    if args.case:
        if not 1 <= args.case <= len(CASES):
            raise SystemExit("--case must be between 1 and 10")
        selected = [CASES[args.case - 1]]

    service = SymptomRAGService()
    try:
        service.warmup(
            languages=(args.language,),
            crops=("cotton", "rice"),
        )
    except Exception as exc:
        print("Embedding warmup failed:", exc)
        return 2

    passed = 0
    print(
        f"V11 language-selected RAG | language={args.language} | "
        f"threshold={service.settings.symptom_match_threshold:.3f} | "
        f"margin={service.settings.symptom_min_margin:.3f}"
    )

    for idx, case in enumerate(selected, 1):
        text = getattr(case, args.language)
        code, mapping, candidates = service.map_one(
            text,
            crop=case.crop,
            affected_part=case.part,
            language=args.language,
        )
        ok = code == case.expected
        passed += int(ok)

        print("\n" + "=" * 88)
        print(f"CASE {idx}: {case.name}")
        print(f"language={args.language} crop={case.crop} part={case.part}")
        print("query:", text)
        print("concept language used:", mapping.retrieval_language.value if mapping.retrieval_language else None)
        for rank, candidate in enumerate(candidates, 1):
            print(
                f"  top{rank}: {candidate.code.value:<28} "
                f"score={candidate.score:.4f} lang={candidate.retrieval_language}"
            )
        print(
            f"{'PASS' if ok else 'FAIL'} predicted={code.value} "
            f"expected={case.expected.value} status={mapping.status} "
            f"score={mapping.similarity:.4f} margin={mapping.margin}"
        )

    print("\n" + "=" * 88)
    print(f"FINAL: {passed}/{len(selected)} passed for language={args.language}")
    return 0 if passed == len(selected) else 1


if __name__ == "__main__":
    raise SystemExit(main())
