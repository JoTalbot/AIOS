#!/usr/bin/env python3
"""
Построить коллекцию aios_personal с качественными мультиязычными эмбеддингами
через fastembed (multilingual-e5 / paraphrase-multilingual).
"""
import json
import sys
sys.path.insert(0, "/root/AIOS")
from pathlib import Path

PERSONAL = Path("/root/AIOS/data/rag/corpus_personal.jsonl")
MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"  # 384d, мультиязычный, 0.22G

chunks = []
for line in PERSONAL.read_text(encoding="utf-8").splitlines():
    try:
        chunks.append(json.loads(line))
    except Exception:
        continue

print(f"Чанков: {len(chunks)}")

# инициализируем fastembed
from fastembed import TextEmbedding
model = TextEmbedding(model_name=MODEL)
print(f"Модель: {MODEL}")

# генерируем эмбеддинги
texts = [c["text"] for c in chunks]
embeddings = list(model.embed(texts))
print(f"Эмбеддингов сгенерировано: {len(embeddings)}")

# пересоздаём коллекцию
import chromadb
from chromadb.config import Settings
client = chromadb.PersistentClient(path="/root/AIOS/chroma_db", settings=Settings(anonymized_telemetry=False))
try:
    client.delete_collection("aios_personal_fast")
except Exception:
    pass
col = client.create_collection("aios_personal_fast")

ids = [c["id"] for c in chunks]
docs = [c["text"] for c in chunks]
metas = [c.get("metadata", {}) for c in chunks]
emb_list = [e.tolist() for e in embeddings]

col.add(ids=ids, documents=docs, metadatas=metas, embeddings=emb_list)
print(f"Коллекция aios_personal_fast построена: {col.count()} чанков")
