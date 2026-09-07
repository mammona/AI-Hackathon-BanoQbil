"""Evaluate V12 clean language-selected symptom RAG.

Focuses on the exact failure cases seen in V11 and prints the actual retrieval
text used for each top candidate so ranking problems are auditable.

Usage:
  python scripts/evaluate_clean_language_rag.py --language punjabi
  python scripts/evaluate_clean_language_rag.py --language urdu
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
    part: str
    expected: SymptomCode
    english: str
    urdu: str
    punjabi: str


CASES = [
    Case("yellowing", "cotton", "leaves", SymptomCode.LEAF_YELLOWING,
         "leaves are turning yellow", "پتے پیلے ہو رہے ہیں", "پتے پیلے ہو رہے نیں"),
    Case("curling", "cotton", "leaves", SymptomCode.LEAF_CURLING,
         "leaves are curling", "پتے مڑ رہے ہیں", "پتے مڑ رہے نیں"),
    Case("brown_spots", "cotton", "leaves", SymptomCode.LEAF_BROWN_SPOTS,
         "brown spots on leaves", "پتوں پر بھورے دھبے ہیں", "پتیاں اُتے بھورے دھبے نیں"),
    Case("white_spots", "cotton", "leaves", SymptomCode.LEAF_WHITE_SPOTS,
         "white spots on leaves", "پتوں پر سفید دھبے ہیں", "پتیاں اُتے چٹے دھبے نیں"),
    Case("wilting", "cotton", "leaves", SymptomCode.LEAF_WILTING,
         "leaves are wilting and drooping", "پتے مرجھا رہے ہیں", "پتے مرجھا رہے نیں"),
    Case("drying", "rice", "leaves", SymptomCode.LEAF_DRYING,
         "leaves are drying", "پتے خشک ہو رہے ہیں", "پتے سک رہے نیں"),
    Case("stem_dark", "cotton", "stem", SymptomCode.STEM_DARKENING,
         "stem is turning black", "تنا کالا ہو رہا ہے", "تنا کالا ہو رہیا اے"),
    Case("boll_rot", "cotton", "boll", SymptomCode.BOLL_ROTTING,
         "cotton bolls are rotting", "ٹینڈے گل سڑ رہے ہیں", "ٹینڈے گل سڑ رہے نیں"),
    Case("panicle_dry", "rice", "panicle", SymptomCode.PANICLE_DRYING,
         "rice panicles are drying", "بالیاں خشک ہو رہی ہیں", "بالیاں سک رہیاں نیں"),
    Case("unknown", "cotton", "leaves", SymptomCode.OTHERS_MAP,
         "sticky sweet material on leaves", "پتوں پر چپچپا میٹھا مادہ ہے", "پتیاں اُتے چپچپا میٹھا مادہ اے"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--language", required=True, choices=["english", "urdu", "punjabi"])
    ap.add_argument("--case", type=int)
    args = ap.parse_args()

    cases = CASES if not args.case else [CASES[args.case - 1]]
    service = SymptomRAGService()
    service.warmup(languages=(args.language,), crops=("cotton", "rice"))

    passed = 0
    for i, case in enumerate(cases, 1):
        q = getattr(case, args.language)
        code, mapping, candidates = service.map_one(
            q, crop=case.crop, affected_part=case.part, language=args.language
        )
        ok = code == case.expected
        passed += int(ok)
        print("\n" + "=" * 96)
        print(f"CASE {i}: {case.name} | language={args.language} | query={q}")
        for rank, c in enumerate(candidates, 1):
            print(f"  top{rank}: {c.code.value:<28} score={c.score:.4f}")
            print(f"        doc: {c.description}")
        print(
            f"{'PASS' if ok else 'FAIL'} predicted={code.value} expected={case.expected.value} "
            f"status={mapping.status} score={mapping.similarity:.4f} margin={mapping.margin}"
        )

    print("\n" + "=" * 96)
    print(f"FINAL {passed}/{len(cases)} passed")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
