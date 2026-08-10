#!/usr/bin/env python3
"""
AIOS RAG - Поиск по эмбеддингам через ChromaDB (Этап 4.3)

Обёртка над ChromaDB PersistentClient. Коллекция может быть:
  - построена на VPS лёгкой локальной эмбеддинг-моделью (default),
  - импортирована из Colab (docs/AIOS_Colab_Embeddings_Build.ipynb) через
    scripts/import_colab_index.py.

Если ChromaDB недоступна - фоллбэк на aios_core.rag.vector_store.VectorStore.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
CHROMA_DIR = REPO_ROOT / "chroma_db"
COLLECTION = "aios_knowledge"

LOG_TAG = "[EmbeddingsStore]"


class EmbeddingsStore:
    def __init__(self, chroma_dir: Optional[Path] = None, collection: str = COLLECTION):
        self.chroma_dir = Path(chroma_dir or CHROMA_DIR)
        self.collection_name = collection
        self._client = None
        self._collection = None
        self._fallback = None
        self._init()

    def _init(self) -> None:
        try:
            import chromadb
            from chromadb.config import Settings
            self.chroma_dir.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=str(self.chroma_dir),
                settings=Settings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(self.collection_name)
            print(f"{LOG_TAG} ChromaDB коллекция '{self.collection_name}' готова ({self.count()} чанков)")
        except Exception as e:
            print(f"{LOG_TAG} [WARN] ChromaDB недоступен ({e}). Фоллбэк на in-memory VectorStore.")
            from aios_core.rag.vector_store import VectorStore
            self._fallback = VectorStore()

    # ------------------------------------------------------------- ingest ----
    def add_chunks(self, chunks: list[dict], use_embeddings: Optional[list] = None) -> int:
        """Добавить чанки (text + metadata). Если use_embeddings None - хэшируем
        встроенным эмбеддингом Chroma (ONNX)."""
        if self._fallback is not None:
            for c in chunks:
                self._fallback.add_document(c.get("id"), c.get("text", ""), c.get("metadata"))
            return len(chunks)
        if self._collection is None:
            return 0
        ids = [c["id"] for c in chunks]
        docs = [c.get("text", "") for c in chunks]
        metas = [c.get("metadata", {}) for c in chunks]
        if use_embeddings is not None:
            self._collection.add(ids=ids, documents=docs, metadatas=metas, embeddings=use_embeddings)
        else:
            self._collection.add(ids=ids, documents=docs, metadatas=metas)
        return len(chunks)

    # ------------------------------------------------------------- query ----
    def search(self, query: str, n_results: int = 5, query_embedding: Optional[list] = None) -> list[dict]:
        if self._fallback is not None:
            return self._fallback.search(query, n_results=n_results)
        if self._collection is None:
            return []
        try:
            kw = {"n_results": n_results}
            if query_embedding is not None:
                kw["query_embeddings"] = [query_embedding]
            else:
                kw["query_texts"] = [query]
            res = self._collection.query(**kw)
            out = []
            for i, doc in enumerate(res["documents"][0]):
                out.append({
                    "text": doc,
                    "id": res["ids"][0][i],
                    "metadata": res["metadatas"][0][i] if res.get("metadatas") else {},
                    "distance": res["distances"][0][i] if res.get("distances") else None,
                })
            return out
        except Exception as e:
            print(f"{LOG_TAG} [WARN] query: {e}")
            return []

    def count(self) -> int:
        if self._fallback is not None:
            return self._fallback.count()
        try:
            return self._collection.count()
        except Exception:
            return 0


if __name__ == "__main__":
    store = EmbeddingsStore()
    print("count:", store.count())
    if store.count() == 0:
        print("Коллекция пуста. Постройте индекс: Colab-ноутбук Embeddings_Build или import_colab_index.py")
