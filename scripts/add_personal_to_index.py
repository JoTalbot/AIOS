#!/usr/bin/env python3
"""Добавить личные чанки (чаты + профиль) в ChromaDB коллекцию ai os_knowledge."""
import json
import sys
sys.path.insert(0, "/root/AIOS")
from pathlib import Path

PERSONAL = Path("/root/AIOS/data/rag/corpus_personal.jsonl")

chunks = []
for line in PERSONAL.read_text(encoding="utf-8").splitlines():
    try:
        chunks.append(json.loads(line))
    except Exception:
        continue

from aios_core.rag.embeddings_store import EmbeddingsStore
store = EmbeddingsStore()
before = store.count()
store.add_chunks(chunks)
after = store.count()
print(f"Добавлено: {len(chunks)} личных чанков (чаты + профиль)")
print(f"Было: {before}, стало: {after}")
