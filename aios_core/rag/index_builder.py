#!/usr/bin/env python3
"""
AIOS RAG - Подготовка корпуса для эмбеддингов (Этап 4.1)

Сканирует базу знаний AIOS, чанкует документы и сохраняет корпус в
data/rag/corpus.jsonl для генерации эмбеддингов в Colab GPU
(docs/AIOS_Colab_Embeddings_Build.ipynb).

Охватываемые источники:
  - aios_core/**/*.py           (исходный код ядра)
  - docs/*.md, *.ipynb          (документация и ноутбуки)
  - README.md, ARCHITECTURE.md  (общая информация)
  - data/knowledge/**, data/Calls/**, data/templates/** (база знаний)

Чанкинг: по ~800 токенов с перекрытием 80. Каждый чанк -> строка JSONL:
  {"id": ..., "text": ..., "metadata": {"type": ..., "path": ...}}
"""

from __future__ import annotations

import os
import re
import json
import tarfile
import argparse
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
RAG_DIR = REPO_ROOT / "data" / "rag"
CORPUS_FILE = RAG_DIR / "corpus.jsonl"
EXPORT_TAR = RAG_DIR / "corpus_export.tar.gz"

# источники: (путь от REPO_ROOT, тип)
SOURCES = [
    ("aios_core", "code"),
    ("docs", "docs"),
    (".", "md"),                 # корневые .md (README, ARCHITECTURE)
    ("data/knowledge", "knowledge"),
    ("data/templates", "knowledge"),
    ("data/Calls", "calls"),
]

CHUNK_CHARS = 3000
OVERLAP_CHARS = 400

SKIP_DIRS = {"__pycache__", "node_modules", ".git", ".benchmarks", "chroma_db"}

LOG_TAG = "[RAGIndexBuilder]"


def _should_include(path: Path, ftype: str) -> bool:
    if any(part in SKIP_DIRS for part in path.parts):
        return False
    if ftype == "code":
        return path.suffix == ".py"
    if ftype == "docs":
        return path.suffix in (".md", ".ipynb", ".txt", ".rst")
    if ftype == "md":
        return path.suffix == ".md"
    if ftype in ("knowledge", "calls"):
        return path.suffix in (".md", ".txt", ".json", ".jsonl", ".csv")
    return False


def _chunk(text: str, doc_id: str, meta: dict) -> list[dict]:
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    chunks = []
    if not text:
        return chunks
    for i in range(0, len(text), CHUNK_CHARS - OVERLAP_CHARS):
        piece = text[i:i + CHUNK_CHARS].strip()
        if not piece:
            continue
        chunks.append({
            "id": f"{doc_id}#{i // (CHUNK_CHARS - OVERLAP_CHARS)}",
            "text": piece,
            "metadata": dict(meta, offset=i),
        })
    return chunks


def build_corpus(output: Optional[Path] = None) -> Path:
    out = Path(output or CORPUS_FILE)
    out.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    seen_docs = 0
    with open(out, "w", encoding="utf-8") as f:
        for rel, ftype in SOURCES:
            base = REPO_ROOT / rel
            if not base.exists():
                continue
            if base.is_file():
                paths = [base]
            else:
                paths = sorted(base.rglob("*"))
            for p in paths:
                if not p.is_file() or not _should_include(p, ftype):
                    continue
                try:
                    text = p.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                doc_id = str(p.relative_to(REPO_ROOT))
                meta = {"type": ftype, "path": doc_id}
                for ch in _chunk(text, doc_id, meta):
                    f.write(json.dumps(ch, ensure_ascii=False) + "\n")
                    total += 1
                seen_docs += 1
        print(f"{LOG_TAG} Проиндексировано документов: {seen_docs}, чанков: {total} -> {out}")
    return out


def export_corpus_tar() -> Optional[str]:
    """Упаковать корпус + пустой chroma для переноса в Colab."""
    archive = RAG_DIR / "corpus_export.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        if CORPUS_FILE.exists():
            tar.add(CORPUS_FILE, arcname="corpus.jsonl")
    return str(archive) if archive.exists() else None


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="AIOS RAG corpus builder")
    ap.add_argument("--export", action="store_true")
    args = ap.parse_args()
    build_corpus()
    if args.export:
        print(f"{LOG_TAG} Экспорт: {export_corpus_tar()}")
