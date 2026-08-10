#!/usr/bin/env python3
"""
AIOS RAG - Импорт индекса эмбеддингов из Colab (Этап 4.3)

Переносит готовый ChromaDB-индекс (построенный в Colab через
docs/AIOS_Colab_Embeddings_Build.ipynb) на VPS.

Варианты:
  1. --src <папка chroma_db из Colab> : рекурсивно копирует в /root/AIOS/chroma_db
  2. --src <архив>.tar.gz  + --extract : распаковывает
  3. --src <corpus.jsonl>  : собирает коллекцию на VPS (ONNX-эмбеддинги Chroma)

Использование:
    python scripts/import_colab_index.py --src /tmp/chroma_colab.tar.gz --extract
"""

from __future__ import annotations

import sys
import tarfile
import shutil
import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHROMA_DIR = REPO_ROOT / "chroma_db"


def main() -> int:
    ap = argparse.ArgumentParser(description="AIOS Import Colab Embeddings Index")
    ap.add_argument("--src", required=True)
    ap.add_argument("--extract", action="store_true", help="src - tar.gz архив")
    args = ap.parse_args()

    src = Path(args.src)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    if args.extract:
        with tarfile.open(src, "r:gz") as tar:
            tmp = REPO_ROOT / "data" / "rag" / "_colab_index"
            if tmp.exists():
                shutil.rmtree(tmp)
            tmp.mkdir(parents=True, exist_ok=True)
            tar.extractall(tmp)
            # ищем папку chroma (с chroma.sqlite3) или корень
            root = tmp
            for cand in tmp.rglob("chroma.sqlite3"):
                root = cand.parent
                break
            for item in root.iterdir():
                dest = CHROMA_DIR / item.name
                if item.is_dir():
                    shutil.copytree(item, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, dest)
            shutil.rmtree(tmp, ignore_errors=True)
    elif src.is_dir():
        for item in src.iterdir():
            dest = CHROMA_DIR / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)
    elif src.suffix == ".jsonl":
        from aios_core.rag.embeddings_store import EmbeddingsStore
        import json
        store = EmbeddingsStore()
        chunks = [json.loads(l) for l in src.read_text(encoding="utf-8").splitlines() if l.strip()]
        store.add_chunks(chunks)
        print(f"Индексировано {len(chunks)} чанков на VPS (локальные эмбеддинги).")
    else:
        print(f"❌ Не распознан источник: {src}")
        return 1

    print(f"✅ Индекс импортирован в {CHROMA_DIR}")
    # проверка
    sys.path.insert(0, str(REPO_ROOT))
    from aios_core.rag.embeddings_store import EmbeddingsStore
    s = EmbeddingsStore()
    print("Чанков в коллекции:", s.count())
    return 0


if __name__ == "__main__":
    sys.exit(main())
