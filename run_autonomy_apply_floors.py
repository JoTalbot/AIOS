#!/usr/bin/env python3
"""
AIOS Autonomy Apply Floors — внести предложенные ценовые полы в конфиг.

Владелец подтверждает рекомендации (из run_autonomy_advice.py), и полы
добавляются в data/price_floors.json (только добавление, существующие не трогаем).

  python run_autonomy_apply_floors.py            # показать что добавится
  python run_autonomy_apply_floors.py --apply    # применить (добавить)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

FLOORS = ROOT / "data" / "price_floors.json"


def _load_floors() -> dict:
    try:
        return json.loads(FLOORS.read_text(encoding="utf-8"))
    except Exception:
        return {"default": 0, "items": {}}


def _save_floors(d: dict) -> None:
    FLOORS.parent.mkdir(parents=True, exist_ok=True)
    FLOORS.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="внести полы в price_floors.json")
    args = ap.parse_args()

    from aios_core.autonomy.report import floor_advice
    adv = floor_advice()
    no_floor = adv.get("items_without_floor", [])
    if not no_floor:
        print("Нет товаров без ценового пола.")
        return 0

    floors = _load_floors()
    items = floors.setdefault("items", {})
    new_entries = {}
    for a in no_floor:
        key = a["item"].strip().lower()
        if key not in items:
            new_entries[key] = a["suggested_floor"]

    if args.apply:
        if not new_entries:
            print("Ничего нового добавить.")
            return 0
        items.update(new_entries)
        _save_floors(floors)
        print(f"✅ Добавлено ценовых полов: {len(new_entries)}")
        for k, v in new_entries.items():
            print(f"  • {k}: {v}")
    else:
        print(f"Будет добавлено полов: {len(new_entries)} (для применения — --apply):")
        for k, v in new_entries.items():
            print(f"  • {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
