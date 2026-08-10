#!/usr/bin/env python3
"""
AIOS RAG - Построение полного индекса эмбеддингов на VPS (Этап 4.3)

Локальная альтернатива Colab-индексу: генерирует эмбеддинги встроенным
ONNX-эмбеддингом ChromaDB (all-MiniLM-L6-v2) для всего корпуса.
Для более точных эмбеддингов (bge-m3) используйте Colab-ноутбук
Embeddings_Build + import_colab_index.py.

    python scripts/build_local_embedding_index.py --chunk-size 200
"""

from __future__ import annotations

import sys
import json
import time
import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aios_core.rag.embeddings_store import EmbeddingsStore  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(REPO_ROOT / "data/rag/corpus.jsonl"))
    ap.add_argument("--chunk-size", type=int, default=200)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=None)
    args = ap.parse_args()

    chunks = [json.loads(l) for l in open(args.corpus, encoding="utf-8") if l.strip()]
    if args.end is not None:
        chunks = chunks[args.start:args.end]
    else:
        chunks = chunks[args.start:]

    store = EmbeddingsStore()
    t0 = time.time()
    done = 0
    for i in range(0, len(chunks), args.chunk_size):
        batch = chunks[i:i + args.chunk_size]
        store.add_chunks(batch)
        done += len(batch)
        if done % 1000 == 0 or done == len(chunks):
            print(f"⏳ {done}/{len(chunks)} чанков | total={store.count()} | "
                  f"{time.time()-t0:.0f}s", flush=True)
    print(f"✅ Готово: {store.count()} чанков в ChromaDB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
