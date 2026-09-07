"""Compare local Qwen3-Embedding with multilingual-e5-small on the same 10 cases."""

from __future__ import annotations

import time

from evaluate_multilingual_retrieval import CASES, make_service, run_cases


def run(name: str, backend: str, model: str) -> None:
    print("\n" + "#" * 90)
    print(f"BACKEND: {name} | {model}")
    print("#" * 90)
    service = make_service(backend, model)
    start = time.perf_counter()
    service.warmup(languages=("urdu",), crops=("cotton", "rice"))
    passed = run_cases(service, CASES)
    elapsed = time.perf_counter() - start
    print(f"{name}: {passed}/{len(CASES)} correct | total warmup+test time={elapsed:.2f}s")


def main() -> int:
    try:
        run("Qwen3 Embedding via Ollama", "ollama", "qwen3-embedding:0.6b")
    except Exception as exc:
        print("Qwen3 embedding benchmark failed:", exc)

    try:
        run("Multilingual E5 Small", "hf_e5", "intfloat/multilingual-e5-small")
    except Exception as exc:
        print("E5 benchmark failed:", exc)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
