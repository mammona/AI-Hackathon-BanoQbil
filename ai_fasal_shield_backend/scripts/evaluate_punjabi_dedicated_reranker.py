"""Run the bundled Punjabi benchmark through V17 dedicated reranking.

Prerequisites:
  ollama pull qwen3-embedding:0.6b
  python -m scripts.prepare_qwen_reranker

Run:
  python -m scripts.evaluate_punjabi_dedicated_reranker
"""
from __future__ import annotations

import argparse
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-id", default=None)
    args = parser.parse_args()

    reports = json.loads(DATASET.read_text(encoding="utf-8"))
    if args.report_id:
        reports = [r for r in reports if r["report_id"] == args.report_id]
        if not reports:
            print(f"Unknown report id: {args.report_id}")
            return 2

    service = SymptomRAGService()
    total = correct = known = unknown = top1 = top3 = top5 = 0

    for report in reports:
        print("\n" + "=" * 100, flush=True)
        print(f"{report['report_id']} | {report['crop']} | {report['answer_1']}", flush=True)
        for item in report["rag_symptoms"]:
            expected = SymptomCode(item["expected_code"])
            debug = service.debug_map_one(
                item["text"],
                crop=report["crop"],
                affected_part=report["affected_part"],
                language=report["language"],
                use_reranker=True,
                top_k=5,
            )
            total += 1
            is_known = expected != SymptomCode.OTHERS_MAP
            codes = [c["code"] for c in debug["candidates"]]
            if is_known:
                known += 1
                top1 += int(bool(codes) and codes[0] == expected.value)
                top3 += int(expected.value in codes[:3])
                top5 += int(expected.value in codes[:5])
            else:
                unknown += 1
            passed = debug["final_code"] == expected.value
            correct += int(passed)

            print(f"symptom : {item['text']}", flush=True)
            print(f"expected: {expected.value}", flush=True)
            for c in debug["candidates"]:
                rr = c.get("reranker_score")
                rr_text = "-" if rr is None else f"{rr:.4f}"
                print(
                    f"  {c['rank']}. {c['code']:<28} embed={c['score']:.4f} rerank={rr_text} | {c['description']}",
                    flush=True,
                )
            print(
                f"final={debug['final_code']} status={debug['status']} "
                f"rerank_reason={debug.get('reranker_reason')} {'PASS' if passed else 'FAIL'}",
                flush=True,
            )

    print("\n" + "#" * 100, flush=True)
    print(f"Total symptoms : {total}", flush=True)
    print(f"Known symptoms : {known}", flush=True)
    print(f"Unknown        : {unknown}", flush=True)
    print(f"Embedding Top1 : {top1}/{known}" if known else "Embedding Top1 : n/a", flush=True)
    print(f"Top3 recall    : {top3}/{known}" if known else "Top3 recall    : n/a", flush=True)
    print(f"Top5 recall    : {top5}/{known}" if known else "Top5 recall    : n/a", flush=True)
    print(f"Final correct  : {correct}/{total} ({100*correct/total:.1f}%)" if total else "Final correct: n/a", flush=True)
    print("#" * 100, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
