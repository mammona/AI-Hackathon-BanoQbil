"""Live V10 diagnostic for meaning-only multilingual symptom retrieval.

Requires local Ollama with qwen3-embedding:0.6b. It prints eligible candidates,
Top-3 scores, margin, and final decision without invoking the generative Qwen model.
"""
from app.constants.symptoms import SymptomCode
from app.services.symptom_rag_service import SymptomRAGService

CASES = [
    ("Urdu yellowing", "urdu", "پتے پیلے ہو رہے ہیں", "cotton", "leaves", SymptomCode.LEAF_YELLOWING),
    ("Urdu curling", "urdu", "پتے مڑ رہے ہیں", "cotton", "leaves", SymptomCode.LEAF_CURLING),
    ("Urdu brown spots", "urdu", "پتوں پر بھورے دھبے ہیں", "cotton", "leaves", SymptomCode.LEAF_BROWN_SPOTS),
    ("Urdu leaf drying", "urdu", "پتے خشک ہو رہے ہیں", "rice", "leaves", SymptomCode.LEAF_DRYING),
    ("Urdu stem darkening", "urdu", "تنا کالا ہو رہا ہے", "cotton", "stem", SymptomCode.STEM_DARKENING),
    ("Urdu plant wilting", "urdu", "پودا مرجھا رہا ہے", "rice", "whole plant", SymptomCode.PLANT_WILTING),
    ("English leaf curling", "english", "leaves are rolling inward", "rice", "leaves", SymptomCode.LEAF_CURLING),
    ("Roman Urdu yellowing", "urdu", "patte peele ho rahe hain", "cotton", "leaves", SymptomCode.LEAF_YELLOWING),
    ("Cotton boll rot", "urdu", "ٹینڈے گل سڑ رہے ہیں", "cotton", "boll", SymptomCode.BOLL_ROTTING),
    ("Unknown sticky symptom", "urdu", "پتوں پر چپچپا مادہ ہے", "cotton", "leaves", SymptomCode.OTHERS_MAP),
]

def main() -> int:
    service = SymptomRAGService()
    passed = 0
    for i, (name, language, text, crop, part, expected) in enumerate(CASES, 1):
        code, mapping, candidates = service.map_one(text, crop=crop, affected_part=part, language=language)
        ok = code == expected
        passed += int(ok)
        print("\n" + "=" * 88)
        print(f"CASE {i}: {name}")
        print(f"language={language} crop={crop} affected_part={part!r}")
        print(f"query={text}")
        eligible = service.eligible_concepts(crop=crop, affected_part=part)
        print(f"eligible_concepts={len(eligible)}")
        for rank, c in enumerate(candidates, 1):
            print(f"  top{rank}: {c.code.value:<28} score={c.score:.4f}")
        print(
            f"{'PASS' if ok else 'FAIL'} predicted={code.value} expected={expected.value} "
            f"status={mapping.status} score={mapping.similarity:.4f} "
            f"margin={mapping.margin}"
        )
    print("\n" + "=" * 88)
    print(f"FINAL: {passed}/{len(CASES)} passed")
    return 0 if passed == len(CASES) else 1

if __name__ == "__main__":
    raise SystemExit(main())
