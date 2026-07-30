#!/usr/bin/env python3
"""
Octopus Semantic RAG Search — семантический поиск по памяти.
Использует Ollama с nomic-embed-text для эмбеддингов.
"""
import os
import json
import time
import hashlib
import asyncio
import logging
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass, field

import httpx
import numpy as np

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("octopus-rag")

# Конфигурация
OLLAMA_URL = "http://127.0.0.1:11434"
EMBED_MODEL = "nomic-embed-text"
INDEX_DIR = Path("/mnt/agents/-Octopus/data/agent_orchestrator/rag_index")
MEMORY_DIRS = [
    "/mnt/agents/-Octopus/experience",
    "/mnt/agents/-Octopus/data/agent_orchestrator/notes",
]

@dataclass
class Document:
    content: str
    path: str
    chunk_id: str
    embedding: Optional[np.ndarray] = None

@dataclass
class SearchResult:
    doc: Document
    score: float
    snippet: str

def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
    """Разбивает текст на чанки."""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = ' '.join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks

def get_file_hash(path: str) -> str:
    """Хэш файла для отслеживания изменений."""
    return hashlib.md5(f"{path}:{os.path.getmtime(path)}".encode()).hexdigest()[:16]

async def get_embedding(text: str) -> np.ndarray:
    """Получает эмбеддинг текста через Ollama."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text}
        )
        response.raise_for_status()
        data = response.json()
        return np.array(data["embedding"])

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Косинусная близость между векторами."""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

async def index_documents() -> int:
    """Индексирует все документы в памяти."""
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = INDEX_DIR / "manifest.json"

    manifest = {"files": {}, "chunks": []}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())

    new_chunks = 0

    for memory_dir in MEMORY_DIRS:
        dir_path = Path(memory_dir)
        if not dir_path.exists():
            continue

        for file_path in dir_path.rglob("*.md"):
            file_hash = get_file_hash(str(file_path))

            # Пропускаем если не изменился
            if manifest["files"].get(str(file_path)) == file_hash:
                continue

            log.info(f"Indexing: {file_path.name}")

            try:
                text = file_path.read_text(errors='ignore')
                chunks = chunk_text(text)

                for chunk in chunks:
                    chunk_id = hashlib.md5(f"{file_path}:{chunk[:100]}".encode()).hexdigest()

                    if chunk_id not in [c["chunk_id"] for c in manifest["chunks"]]:
                        embedding = await get_embedding(chunk)
                        manifest["chunks"].append({
                            "chunk_id": chunk_id,
                            "path": str(file_path),
                            "content": chunk,
                            "embedding": embedding.tolist(),
                            "timestamp": time.time()
                        })
                        new_chunks += 1

            except Exception as e:
                log.error(f"Error indexing {file_path}: {e}")

            manifest["files"][str(file_path)] = file_hash

    # Сохраняем манифест
    manifest_path.write_text(json.dumps(manifest, indent=2))
    log.info(f"Indexed {new_chunks} new chunks. Total: {len(manifest['chunks'])}")

    return new_chunks

async def search(query: str, top_k: int = 5) -> List[SearchResult]:
    """Семантический поиск по запросу."""
    manifest_path = INDEX_DIR / "manifest.json"

    if not manifest_path.exists():
        return []

    manifest = json.loads(manifest_path.read_text())

    # Эмбеддинг запроса
    query_embedding = await get_embedding(query)

    results = []
    for chunk in manifest["chunks"]:
        chunk_vec = np.array(chunk["embedding"])
        score = cosine_similarity(query_embedding, chunk_vec)
        results.append(SearchResult(
            doc=Document(
                content=chunk["content"],
                path=chunk["path"],
                chunk_id=chunk["chunk_id"]
            ),
            score=score,
            snippet=chunk["content"][:200] + "..."
        ))

    # Топ-K результатов
    results.sort(key=lambda x: x.score, reverse=True)
    return results[:top_k]

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Octopus RAG Search")
    parser.add_argument("--index", action="store_true", help="Index all documents")
    parser.add_argument("--search", type=str, help="Search query")
    parser.add_argument("--top", type=int, default=5, help="Top K results")
    args = parser.parse_args()

    if args.index:
        await index_documents()
    elif args.search:
        results = await search(args.search, args.top)
        if not results:
            print("No results. Run with --index first.")
            return
        print(f"\n🔍 Search: {args.search}\n")
        for i, r in enumerate(results, 1):
            print(f"{i}. [{r.score:.3f}] {r.doc.path}")
            print(f"   {r.snippet}\n")
    else:
        # Интерактивный режим
        print("Octopus RAG Search (type 'quit' to exit)")
        await index_documents()
        while True:
            query = input("\n🔍 Query: ")
            if query.lower() in ('quit', 'exit', 'q'):
                break
            if not query.strip():
                continue
            results = await search(query)
            if not results:
                print("No results found.")
                continue
            print(f"\nFound {len(results)} results:")
            for i, r in enumerate(results, 1):
                print(f"{i}. [{r.score:.3f}] {r.doc.path}")

if __name__ == "__main__":
    asyncio.run(main())
