"""Vector Store — лёгкое in-memory векторное хранилище для RAG.

Реализует минимальный контракт поиска по документам без внешних
зависимостей (ChromaDB опциональна в проде). Сходство — косинусная
близость TF-векторов по словарю всех документов.
"""

from __future__ import annotations

import math
import re
from typing import Any

_TOKEN_RE = re.compile(r"[\w]+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    """Разбить текст на lowercased токены."""
    return _TOKEN_RE.findall(text.lower())


class VectorStore:
    """Простое векторное хранилище документов (in-memory)."""

    def __init__(self, persist_dir: str | None = None) -> None:
        self.persist_dir = persist_dir
        self._docs: dict[str, dict[str, Any]] = {}

    def add_document(self, doc_id: str, text: str, metadata: dict[str, Any] | None = None) -> None:
        """Добавить или обновить документ."""
        self._docs[doc_id] = {
            "id": doc_id,
            "text": text,
            "metadata": metadata or {},
            "tokens": _tokenize(text),
        }

    @staticmethod
    def _score(query_tokens: list[str], doc_tokens: list[str]) -> float:
        """Косинусная близость по частотам токенов."""
        if not query_tokens or not doc_tokens:
            return 0.0
        q_freq: dict[str, int] = {}
        for t in query_tokens:
            q_freq[t] = q_freq.get(t, 0) + 1
        d_freq: dict[str, int] = {}
        for t in doc_tokens:
            d_freq[t] = d_freq.get(t, 0) + 1
        common = set(q_freq) & set(d_freq)
        dot = sum(q_freq[t] * d_freq[t] for t in common)
        q_norm = math.sqrt(sum(v * v for v in q_freq.values()))
        d_norm = math.sqrt(sum(v * v for v in d_freq.values()))
        if q_norm == 0 or d_norm == 0:
            return 0.0
        return dot / (q_norm * d_norm)

    def search(self, query: str, n_results: int = 5) -> list[dict[str, Any]]:
        """Вернуть до n_results документов, отсортированных по сходству."""
        if not self._docs or n_results <= 0:
            return []
        query_tokens = _tokenize(query)
        scored = [(self._score(query_tokens, doc["tokens"]), doc) for doc in self._docs.values()]
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                "id": doc["id"],
                "text": doc["text"],
                "document": doc["text"],
                "metadata": doc["metadata"],
                "score": score,
            }
            for score, doc in scored[:n_results]
        ]

    def count(self) -> int:
        """Количество документов в хранилище."""
        return len(self._docs)

    def delete(self, doc_id: str) -> None:
        """Удалить документ по идентификатору."""
        self._docs.pop(doc_id, None)

    def stats(self) -> dict[str, Any]:
        """Краткая статистика хранилища."""
        return {"documents": len(self._docs), "persist_dir": self.persist_dir}
