#!/usr/bin/env python3
"""AIOS - Генератор ноутбука построения эмбеддингов (Этап 4.2)."""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path("/root/AIOS")
DOCS = REPO / "docs"


def md(s: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": s.splitlines(keepends=True)}


def code(s: str) -> dict:
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": s.splitlines(keepends=True)}


def base_meta():
    return {"colab": {"provenance": []}, "kernelspec": {"name": "python3", "display_name": "Python 3"},
            "language_info": {"name": "python"}}


def nb() -> dict:
    cells = [
        md(
            "# 🔎 AIOS Embeddings & RAG Index Build\n\n"
            "Генерация эмбеддингов для всей базы знаний AIOS на **GPU Colab** (BAAI/bge-m3, nomic-embed-text) "
            "и сохранение векторного индекса в **ChromaDB** для мгновенного поиска на VPS.\n\n"
            "**T4 GPU / High-RAM CPU**.\n\n"
            "1. Загрузите `corpus.jsonl` (с VPS: папка `data/rag/`, получить `python aios_core/rag/index_builder.py --export`).\n"
            "2. Выполните ячейки.\n"
            "3. Скачайте папку `chroma_colab/` на VPS и запустите `scripts/import_colab_index.py --src <архив> --extract`."
        ),
        code("!pip install -q chromadb sentence-transformers torch\n"
             "from sentence_transformers import SentenceTransformer\n"
             "import torch\n"
             "print('✅ Установлено, CUDA:', torch.cuda.is_available())"),
        code("# === ЯЧЕЙКА 2: Загрузка корпуса ===\n"
             "import json, os\n"
             "chunks = [json.loads(l) for l in open('corpus.jsonl', encoding='utf-8') if l.strip()]\n"
             "print('✅ Чанков в корпусе:', len(chunks))\n"
             "print('Пример:', chunks[0]['text'][:120])"),
        code("# === ЯЧЕЙКА 3: Модель эмбеддингов ===\n"
             "# BAAI/bge-m3 (мультиязычная, 1024) — рекомендована. Альтернатива: nomic-embed-text-v1.5\n"
             "model = SentenceTransformer('BAAI/bge-m3')\n"
             "print('✅ Модель загружена, размерность:', model.get_sentence_embedding_dimension())"),
        code("# === ЯЧЕЙКА 4: Генерация эмбеддингов (батчами) ===\n"
             "texts = [c['text'] for c in chunks]\n"
             "embs = model.encode(texts, batch_size=32, show_progress_bar=True, normalize_embeddings=True)\n"
             "print('✅ Эмбеддинги:', embs.shape)"),
        code("# === ЯЧЕЙКА 5: Сохранение в ChromaDB ===\n"
             "import chromadb\n"
             "from chromadb.config import Settings\n"
             "client = chromadb.PersistentClient(path='chroma_colab', settings=Settings(anonymized_telemetry=False))\n"
             "col = client.get_or_create_collection('aios_knowledge')\n"
             "# добавляем батчами (экономно по памяти)\n"
             "B = 512\n"
             "for i in range(0, len(chunks), B):\n"
             "    c = chunks[i:i+B]\n"
             "    col.add(ids=[x['id'] for x in c],\n"
             "            documents=[x['text'] for x in c],\n"
             "            metadatas=[x['metadata'] for x in c],\n"
             "            embeddings=embs[i:i+B].tolist())\n"
             "print('✅ В коллекции:', col.count())"),
        code("# === ЯЧЕЙКА 6: Тест поиска ===\n"
             "res = col.query(query_texts=['как зарегистрировать сервис в реестре Colab?'], n_results=3)\n"
             "for d in res['documents'][0]:\n"
             "    print(' -', d[:120])\n"
             "print('\\n✅ Индекс готов')\n"
             "!tar -czf chroma_colab.tar.gz chroma_colab\n"
             "print('Скачайте chroma_colab.tar.gz на VPS и запустите: scripts/import_colab_index.py --src chroma_colab.tar.gz --extract')"),
    ]
    return {"cells": cells, "metadata": base_meta(), "nbformat": 4, "nbformat_minor": 0}


if __name__ == "__main__":
    p = DOCS / "AIOS_Colab_Embeddings_Build.ipynb"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(nb(), indent=1), encoding="utf-8")
    print(f"✅ {p} ({p.stat().st_size} байт)")
