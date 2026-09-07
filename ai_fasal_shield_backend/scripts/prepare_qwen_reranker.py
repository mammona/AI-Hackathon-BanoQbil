"""Download and verify the dedicated Qwen3 symptom reranker before the demo.

Run from backend root:
    python -m scripts.prepare_qwen_reranker

This downloads Qwen/Qwen3-Reranker-0.6B (~1.2 GB) into the normal Hugging Face
cache. After this succeeds, the backend can use the reranker from cache.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from huggingface_hub import snapshot_download

from app.config import get_settings
from app.services.symptom_rag_service import Qwen3DedicatedReranker


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--download-only",
        action="store_true",
        help="Download files without loading the model into RAM/VRAM.",
    )
    args = parser.parse_args()

    settings = get_settings()
    model_name = settings.symptom_reranker_model
    print(f"Downloading/caching: {model_name}", flush=True)
    path = snapshot_download(repo_id=model_name)
    print(f"Cached at: {path}", flush=True)

    if args.download_only:
        print("Download complete.", flush=True)
        return 0

    print("Loading and running one Punjabi verification pair...", flush=True)
    reranker = Qwen3DedicatedReranker(
        model_name=model_name,
        device=settings.symptom_reranker_device,
        max_length=settings.symptom_reranker_max_length,
        min_score=settings.symptom_reranker_min_score,
        min_margin=settings.symptom_reranker_min_margin,
        local_files_only=True,
    )
    result = reranker.warmup()
    print(result, flush=True)
    if not result.get("ready"):
        print("Reranker verification failed.", flush=True)
        return 1
    print("Dedicated reranker is ready.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
