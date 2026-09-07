"""Focused live check that wording variants map to the same concept by meaning.

No symptom alias table is used. Each phrase is embedded directly with the same
meaning-only multilingual RAG service.
"""

from app.constants.symptoms import SymptomCode
from app.services.symptom_rag_service import SymptomRAGService


CASES = [
    ("Urdu plural", "urdu", "پتے پیلے ہو رہے ہیں"),
    ("Urdu singular", "urdu", "پتا پیلا ہو رہا ہے"),
    ("Punjabi Shahmukhi", "punjabi", "پتے پیلے ہو رہے نیں"),
    ("Punjabi singular", "punjabi", "پتا پیلا ہو رہیا اے"),
    ("Roman Urdu diagnostic", "urdu", "patte peele ho rahe hain"),
    ("English", "english", "the leaves are turning yellow"),
]


def main() -> int:
    service = SymptomRAGService()
    service.warmup(languages=("english", "urdu", "punjabi"), crops=("cotton",))
    passed = 0
    for idx, (name, language, text) in enumerate(CASES, 1):
        code, mapping, candidates = service.map_one(
            text, crop="cotton", affected_part="leaves", language=language
        )
        ok = code == SymptomCode.LEAF_YELLOWING
        passed += int(ok)
        print("\n" + "=" * 78)
        print(f"CASE {idx}: {name}")
        print("Language:", language)
        print("Query:", text)
        for rank, c in enumerate(candidates, 1):
            print(f"  top{rank}: {c.code.value:<26} similarity={c.score:.4f}")
        print(
            f"{'PASS' if ok else 'FAIL'} predicted={code.value} "
            f"expected=LEAF_YELLOWING status={mapping.status} "
            f"margin={mapping.margin}"
        )

    print("\n" + "=" * 78)
    print(f"FINAL: {passed}/{len(CASES)} yellowing variants passed")
    return 0 if passed == len(CASES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
