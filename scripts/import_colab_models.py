#!/usr/bin/env python3
"""
AIOS Quant ML Engine - Импорт моделей, обученных в Colab (Этап 2.3)

Копирует файлы моделей (catboost_price_dir.cbm/.pkl, ppo_trader.zip и др.)
в data/quant/models/ для использования QuantMLPredictor на VPS.

Источники:
  - папка, указанная в --src (например, смонтированный датасет / загруженный архив),
  - локальный путь.

Использование:
    python scripts/import_colab_models.py --src /path/to/exported_models
    python scripts/import_colab_models.py --src models.tar.gz --extract
"""

from __future__ import annotations

import sys
import tarfile
import shutil
import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = REPO_ROOT / "data" / "quant" / "models"

ALLOWED_EXTS = {".cbm", ".pkl", ".joblib", ".zip", ".onnx", ".json", ".bin"}


def main() -> int:
    ap = argparse.ArgumentParser(description="AIOS Import Colab Models")
    ap.add_argument("--src", required=True, help="Папка или архив с моделями")
    ap.add_argument("--extract", action="store_true", help="Если src - tar.gz архив")
    args = ap.parse_args()

    src = Path(args.src)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    files: list[Path] = []
    if args.extract:
        with tarfile.open(src, "r:gz") as tar:
            tmp = REPO_ROOT / "data" / "quant" / "_colab_import"
            tmp.mkdir(parents=True, exist_ok=True)
            tar.extractall(tmp)
            files = [p for p in tmp.rglob("*") if p.is_file() and p.suffix.lower() in ALLOWED_EXTS]
            src = tmp
    elif src.is_dir():
        files = [p for p in src.rglob("*") if p.is_file() and p.suffix.lower() in ALLOWED_EXTS]
    elif src.is_file() and src.suffix.lower() in ALLOWED_EXTS:
        files = [src]
    else:
        print(f"❌ Не найден источник: {src}")
        return 1

    if not files:
        print("⚠️ Не найдено файлов моделей с допустимыми расширениями")
        return 1

    imported = []
    for f in files:
        dest = MODELS_DIR / f.name
        shutil.copy2(f, dest)
        imported.append(dest.name)
        print(f"✅ {f.name} -> {dest}")

    print(f"\nИмпортировано {len(imported)} моделей в {MODELS_DIR}")
    print("QuantMLPredictor подхватит их при следующем запуске инференса.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
