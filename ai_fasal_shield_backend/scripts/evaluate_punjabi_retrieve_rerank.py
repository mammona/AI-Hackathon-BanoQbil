"""Run the 10-report Punjabi benchmark through V13 retrieve -> rerank logic.

Requires local Ollama with:
  ollama pull qwen3:1.7b
  ollama pull qwen3-embedding:0.6b

Run from backend root:
  python -m scripts.evaluate_punjabi_retrieve_rerank
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.constants.symptoms import SymptomCode
from app.services.symptom_rag_service import SymptomRAGService

DATASET = ROOT / "evaluation" / "punjabi_rag_10_reports.json"


def main() -> int:
    reports = json.loads(DATASET.read_text(encoding="utf-8"))
    service = SymptomRAGService()
    total = correct = top5 = reranked = direct = 0

    for report in reports:
        print("\n" + "=" * 100)
        print(report["report_id"], report["answer_1"])
        for item in report["rag_symptoms"]:
            total += 1
            expected = SymptomCode(item["expected_code"])
            debug = service.debug_map_one(
                item["text"],
                crop=report["crop"],
                affected_part=report["affected_part"],
                language=report["language"],
                use_reranker=True,
                top_k=5,
            )
            codes = [c["code"] for c in debug["candidates"]]
            if expected != SymptomCode.OTHERS_MAP and expected.value in codes[:5]:
                top5 += 1
            if debug["reranker_used"]:
                reranked += 1
            else:
                direct += 1
            passed = debug["final_code"] == expected.value
            correct += int(passed)

            print(f"symptom : {item['text']}")
            print(f"expected: {expected.value}")
            for c in debug["candidates"]:
                print(f"  {c['rank']}. {c['code']:<28} {c['score']:.4f} | {c['description']}")
            print(
                f"final={debug['final_code']} status={debug['status']} "
                f"stage={debug['decision_stage']} {'PASS' if passed else 'FAIL'}"
            )

    print("\n" + "#" * 100)
    print(f"Total mappings        : {total}")
    print(f"Final correct         : {correct}/{total} ({100*correct/total:.1f}%)")
    print(f"Known expected in Top5: {top5}")
    print(f"Direct decisions      : {direct}")
    print(f"Reranked decisions    : {reranked}")
    print("#" * 100)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
