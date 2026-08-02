#!/usr/bin/env python3
"""
AIOS Finance — учёт продаж и расходов авторазборки.
  python run_finance.py add sale|expense <сумма> <описание>
  python run_finance.py report [дней]
  python run_finance.py list [N]
Данные: data/finance.json
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "finance.json"


def _load() -> list[dict]:
    try:
        return json.loads(DATA.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(items: list[dict]) -> None:
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def add(kind: str, amount: float, desc: str, date: str | None = None) -> dict:
    if kind not in ("sale", "expense"):
        return {"status": "error", "error": "kind = sale|expense"}
    if amount <= 0:
        return {"status": "error", "error": "Сумма должна быть > 0"}
    items = _load()
    items.append({
        "kind": kind,
        "amount": float(amount),
        "desc": desc or ("продажа" if kind == "sale" else "расход"),
        "date": date or datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    _save(items)
    return {"status": "ok", "entry": items[-1], "total": len(items)}


def report(days: int = 30) -> dict:
    items = _load()
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    recent = [x for x in items if x["date"][:10] >= since]
    sales = sum(x["amount"] for x in recent if x["kind"] == "sale")
    exp = sum(x["amount"] for x in recent if x["kind"] == "expense")
    return {
        "status": "ok",
        "days": days,
        "sales": round(sales, 2),
        "expenses": round(exp, 2),
        "profit": round(sales - exp, 2),
        "count": len(recent),
    }


def listing(n: int = 10) -> dict:
    items = _load()[-n:][::-1]
    return {"status": "ok", "entries": items}


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    if cmd == "add" and len(sys.argv) >= 4:
        kind = sys.argv[2]
        try:
            amount = float(sys.argv[3])
        except ValueError:
            print(json.dumps({"status": "error", "error": "Неверная сумма"})); return
        desc = " ".join(sys.argv[4:])
        print(json.dumps(add(kind, amount, desc), ensure_ascii=False))
    elif cmd == "report":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        print(json.dumps(report(days), ensure_ascii=False))
    elif cmd == "list":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        print(json.dumps(listing(n), ensure_ascii=False))
    else:
        print(json.dumps({"status": "error", "error": "add|report|list"}))


if __name__ == "__main__":
    main()
