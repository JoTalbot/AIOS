#!/usr/bin/env python3
"""Построить отдельную ChromaDB коллекцию 'aios_personal' из личного корпуса."""
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
# используем ту же инфраструктуру, но отдельную коллекцию
store = EmbeddingsStore(collection="aios_personal")
before = store.count()
# если коллекция уже не пустая - добавим, иначе создастся
store.add_chunks(chunks)
after = store.count()
print(f"Личных чанков в коллекции aios_personal: было {before}, стало {after}")
