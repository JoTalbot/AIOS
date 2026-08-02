#!/usr/bin/env python3
"""
AIOS Inventory — учёт запчастей на складе авторазборки.
  python run_inventory.py add "<название>" <кол-во> <цена> [категория]
  python run_inventory.py list [категория]
  python run_inventory.py search <запрос>
  python run_inventory.py take "<название>" <кол-во>   (списать)
  python run_inventory.py stats
Данные: data/inventory.json
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "inventory.json"


def _load() -> list[dict]:
    try:
        return json.loads(DATA.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(items: list[dict]) -> None:
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def _find(items, name: str):
    """Найти по имени (точное или частичное)."""
    name_l = name.lower()
    for it in items:
        if it["name"].lower() == name_l:
            return it
    for it in items:
        if name_l in it["name"].lower():
            return it
    return None


def add(name: str, qty: int, price: float, category: str = "") -> dict:
    items = _load()
    it = _find(items, name)
    if it:
        it["qty"] = int(it.get("qty", 0)) + qty
        if price:
            it["price"] = float(price)
        msg = f"добавлено (итого {it['qty']})"
    else:
        it = {"name": name, "qty": qty, "price": float(price or 0),
              "category": category or "общее", "added": datetime.now().strftime("%Y-%m-%d %H:%M")}
        items.append(it)
        msg = "новая деталь"
    _save(items)
    return {"status": "ok", "item": it, "msg": msg, "total": len(items)}


def take(name: str, qty: int = 1) -> dict:
    items = _load()
    it = _find(items, name)
    if not it:
        return {"status": "error", "error": f"«{name}» нет на складе"}
    if it["qty"] < qty:
        return {"status": "error", "error": f"На складе только {it['qty']} шт «{it['name']}»"}
    it["qty"] -= qty
    _save(items)
    return {"status": "ok", "item": it, "msg": f"списано {qty} шт"}


def search(query: str) -> dict:
    items = _load()
    q = query.lower()
    found = [it for it in items if q in it["name"].lower() or q in it.get("category", "").lower()]
    return {"status": "ok", "items": found, "count": len(found)}


def listing(category: str | None = None) -> dict:
    items = _load()
    if category:
        items = [it for it in items if it.get("category", "").lower() == category.lower()]
    items = sorted(items, key=lambda x: x.get("qty", 0) == 0)  # пустые в конец
    return {"status": "ok", "items": items, "count": len(items)}


def stats() -> dict:
    items = _load()
    total_qty = sum(it.get("qty", 0) for it in items)
    total_value = sum(it.get("qty", 0) * it.get("price", 0) for it in items)
    zero = [it["name"] for it in items if it.get("qty", 0) == 0]
    return {"status": "ok", "items_count": len(items), "total_qty": total_qty,
            "total_value": round(total_value, 2), "out_of_stock": zero}


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "add" and len(sys.argv) >= 4:
        name = sys.argv[2]
        try:
            qty = int(sys.argv[3])
            price = float(sys.argv[4]) if len(sys.argv) > 4 else 0
        except ValueError:
            print(json.dumps({"status": "error", "error": "кол-во и цена"})); return
        cat = sys.argv[5] if len(sys.argv) > 5 else ""
        print(json.dumps(add(name, qty, price, cat), ensure_ascii=False))
    elif cmd == "take" and len(sys.argv) >= 3:
        qty = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        print(json.dumps(take(sys.argv[2], qty), ensure_ascii=False))
    elif cmd == "search" and len(sys.argv) >= 3:
        print(json.dumps(search(sys.argv[2]), ensure_ascii=False))
    elif cmd == "list":
        cat = sys.argv[2] if len(sys.argv) > 2 else None
        print(json.dumps(listing(cat), ensure_ascii=False))
    elif cmd == "stats":
        print(json.dumps(stats(), ensure_ascii=False))
    else:
        print(json.dumps({"status": "error", "error": "add|take|search|list|stats"}))


if __name__ == "__main__":
    main()
