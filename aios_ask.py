#!/usr/bin/env python3
"""
AIOS - Унифицированный RAG-поиск по знаниям проекта, чатов и профиля владельца
с генерацией ответа через локальную LLM (Ollama qwen).

Использование:
    python aios_ask.py "вопрос про проект"
    python aios_ask.py --llm "вопрос"     # с генерацией ответа LLM
"""
from __future__ import annotations

import sys
import json
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = "qwen2.5-coder:1.5b"


def search_all(query: str, n_per: int = 4) -> list[dict]:
    """Поиск по коллекциям aios_knowledge (проект) и aios_personal_fast (чаты+профиль)."""
    from aios_core.rag.embeddings_store import EmbeddingsStore
    results = []
    try:
        k = EmbeddingsStore(collection="aios_knowledge")
        results += [dict(r, collection="project") for r in k.search(query, n_results=n_per)]
    except Exception as e:
        print(f"[warn] knowledge: {e}", file=sys.stderr)

    # личные данные — через fastembed мультиязычную модель (более точная семантика)
    try:
        from fastembed import TextEmbedding
        import chromadb
        from chromadb.config import Settings
        client = chromadb.PersistentClient(path="/root/AIOS/chroma_db",
                                           settings=Settings(anonymized_telemetry=False))
        try:
            col = client.get_collection("aios_personal_fast")
            model = TextEmbedding(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
            qe = list(model.embed([query]))[0].tolist()
            res = col.query(query_embeddings=[qe], n_results=n_per)
            for i, doc in enumerate(res["documents"][0]):
                results.append({
                    "id": res["ids"][0][i],
                    "text": doc,
                    "distance": res["distances"][0][i] if res.get("distances") else None,
                    "collection": "personal",
                })
        except Exception:
            # фоллбэк на старую коллекцию
            p = EmbeddingsStore(collection="aios_personal")
            results += [dict(r, collection="personal") for r in p.search(query, n_results=n_per)]
    except Exception as e:
        print(f"[warn] personal: {e}", file=sys.stderr)
    return results


def generate_llm(query: str, context: list[dict]) -> str:
    """Генерирует ответ через локальную Ollama."""
    ctx_text = "\n\n".join(f"[{r['collection']}] {r['text'][:500]}" for r in context)
    prompt = (
        "Ты — помощник в системе AIOS. Ответь на вопрос, опираясь ТОЛЬКО на предоставленный контекст. "
        "Если в контексте нет ответа — так и скажи. Отвечай кратко и по делу.\n\n"
        f"КОНТЕКСТ:\n{ctx_text}\n\n"
        f"ВОПРОС: {query}\n\n"
        "ОТВЕТ:"
    )
    body = json.dumps({"model": OLLAMA_MODEL, "prompt": prompt,
                       "stream": False, "options": {"temperature": 0.2}}).encode()
    req = urllib.request.Request(OLLAMA_URL + "/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read())
            return data.get("response", "").strip()
    except Exception as e:
        return f"[LLM недоступен: {e}]"


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("query", help="вопрос")
    ap.add_argument("--llm", action="store_true", help="генерировать ответ LLM")
    ap.add_argument("--top", type=int, default=5)
    args = ap.parse_args()

    res = search_all(args.query, n_per=args.top)
    print(f"=== Результаты поиска ({len(res)}) ===")
    for r in res:
        print(f"[{r['collection']}] {r['id']} (d={r.get('distance','-')})")
        print(f"    {r['text'][:150]}")

    if args.llm and res:
        print("\n=== Ответ LLM ===")
        print(generate_llm(args.query, res))


if __name__ == "__main__":
    main()
