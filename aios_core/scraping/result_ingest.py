#!/usr/bin/env python3
"""
AIOS Scraper Farm - Приём и нормализация результатов скрапинга (Этап 5)

Результаты, собранные Colab-нодами (или локальным скрапером), загружаются на
VPS и ингестируются: сохраняются в data/scraping/results/ и, при наличии
коллекции, добавляются в ChromaDB (RAG) как новые документы.

Ожидаемый формат результата: JSON list of dicts.
"""

from __future__ import annotations

import json
import time
import hashlib
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "data" / "scraping" / "results"


def ingest_results(
    items: list[dict],
    source: str,
    results_dir: Optional[Path] = None,
    to_rag: bool = True,
) -> dict:
    d = Path(results_dir or RESULTS_DIR)
    d.mkdir(parents=True, exist_ok=True)

    seen = set()
    rows = []
    for it in items:
        if not isinstance(it, dict):
            continue
        # дедупликация по url/hash
        key = it.get("url") or it.get("id") or hashlib.md5(
            json.dumps(it, sort_keys=True).encode()).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        rows.append({"source": source, **it})

    fname = f"{source}_{int(time.time())}.json"
    out = d / fname
    out.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    rag_added = 0
    if to_rag and rows:
        try:
            from aios_core.rag.embeddings_store import EmbeddingsStore
            store = EmbeddingsStore()
            chunks = []
            for i, r in enumerate(rows):
                text = r.get("title") or r.get("text") or r.get("name") or ""
                url = r.get("url", "")
                if text:
                    body = f"{text}\nURL: {url}" if url else text
                    chunks.append({
                        "id": f"scrape-{source}-{i}-{hashlib.md5(body.encode()).hexdigest()[:8]}",
                        "text": body,
                        "metadata": {"type": "scrape", "source": source, **{k: v for k, v in r.items() if k != "text"}},
                    })
            if chunks:
                store.add_chunks(chunks)
                rag_added = len(chunks)
        except Exception as e:
            print(f"[ResultIngest] RAG ingest skip: {e}")

    return {"file": str(out), "items": len(rows), "rag_added": rag_added, "source": source}


if __name__ == "__main__":
    import argparse
    import sys
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--input", required=True, help="JSON-файл или JSONL с результатами")
    ap.add_argument("--no-rag", action="store_true")
    args = ap.parse_args()

    data = []
    if args.input.endswith(".jsonl"):
        data = [json.loads(l) for l in open(args.input, encoding="utf-8") if l.strip()]
    else:
        data = json.loads(open(args.input, encoding="utf-8").read())
        if isinstance(data, dict):
            data = data.get("items") or data.get("results") or [data]
    print(json.dumps(ingest_results(data, args.source, to_rag=not args.no_rag),
                     indent=2, ensure_ascii=False))
