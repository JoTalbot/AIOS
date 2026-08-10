#!/usr/bin/env python3
"""
AIOS RAG - Генерация ответов на основе RAG + локальной LLM (улучшение P0/P1)

Связывает поиск по эмбеддингам (ChromaDB) с генерацией ответа локальной
моделью через Ollama (порт 11434). Запрос -> топ-N чанков -> контекст ->
LLM-ответ со ссылками на источники.

Это замыкает RAG-контур полностью локально на VPS (без облачных LLM).

Использование:
    from aios_core.rag.rag_query_llm import RAGQueryLLM
    rag = RAGQueryLLM(model="qwen2.5-coder:1.5b")
    ans = rag.answer("Как зарегистрировать сервис в реестре Colab?")
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Optional

from .embeddings_store import EmbeddingsStore

REPO_ROOT = Path(__file__).resolve().parents[2]
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

LOG_TAG = "[RAGQueryLLM]"

DEFAULT_MODEL = "qwen2.5-coder:1.5b"


class RAGQueryLLM:
    def __init__(self, model: str = DEFAULT_MODEL, n_context: int = 4):
        self.model = model
        self.n_context = n_context
        self.store = EmbeddingsStore()

    def retrieve(self, query: str, n: int | None = None) -> list[dict]:
        """Топ-N чанков из ChromaDB."""
        return self.store.search(query, n_results=n or self.n_context)

    def _call_ollama(self, prompt: str, system: str, timeout: int = 120) -> str:
        payload = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {"temperature": 0.3},
        }).encode("utf-8")
        req = urllib.request.Request(
            OLLAMA_URL, data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("response", "").strip()

    def answer(self, query: str, include_sources: bool = True) -> dict:
        chunks = self.retrieve(query)
        if not chunks:
            return {"query": query, "answer": "Не найдено контекста в базе знаний.",
                    "sources": [], "context": []}

        context_text = "\n\n".join(
            f"[Источник {i+1}] {c['text']}" for i, c in enumerate(chunks)
        )
        system = (
            "Ты - AIOS ассистент. Отвечай на русском, кратко и по делу. "
            "Основывайся ТОЛЬКО на предоставленном контексте. "
            "Если в контексте нет ответа - так и скажи."
        )
        prompt = f"Контекст:\n{context_text}\n\nВопрос: {query}\n\nОтвет:"
        try:
            answer = self._call_ollama(prompt, system)
        except Exception as e:
            answer = f"[Ошибка LLM: {e}]"
            return {"query": query, "answer": answer, "sources": [],
                    "context": chunks, "error": str(e)}

        sources = []
        if include_sources:
            for c in chunks:
                meta = c.get("metadata") or {}
                sources.append({"path": meta.get("path"), "type": meta.get("type"),
                                "id": c.get("id")})

        return {"query": query, "answer": answer, "sources": sources, "context": chunks}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="?", default="Как зарегистрировать сервис в реестре Colab?")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--no-sources", action="store_true")
    args = ap.parse_args()

    rag = RAGQueryLLM(model=args.model)
    res = rag.answer(args.query, include_sources=not args.no_sources)
    print(f"\nВопрос: {res['query']}\n")
    print(f"Ответ:\n{res['answer']}\n")
    if res.get("sources"):
        print("Источники:")
        for s in res["sources"][:3]:
            print(f"  - {s.get('path')} ({s.get('type')})")
