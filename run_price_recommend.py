#!/usr/bin/env python3
"""
Рекомендатор цен на основе рынка OLX (данные коллектора olx_http.sqlite).

Для каждой детали склада/наблюдения считает статистику активных объявлений
конкурентов (n/min/median/max) и сравнивает с нашей ценой:
выше рынка / ниже рынка / в рынке. Данные копятся после добавления запросов
в коллектор; при <5 совпадений — «мало данных».
"""
from __future__ import annotations

import json
import re
import sqlite3
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "olx_http.sqlite"
MIN_SAMPLES = 5


def _tokens(name: str) -> list[str]:
    return [t for t in re.split(r"[^a-zа-яєіїґ0-9]+", str(name).lower()) if len(t) >= 3]


def market_stats(part: str, conn: sqlite3.Connection) -> dict:
    tokens = _tokens(part)
    if not tokens:
        return {"part": part, "n": 0}
    head, rest = tokens[0], tokens[1:]
    prices = []
    for title, price in conn.execute(
            "select title, price_value from ads where active=1 and price_value>0"):
        tl = str(title).lower()
        if head in tl and sum(1 for t in rest if t in tl) >= 1:
            prices.append(float(price))
    if len(prices) < MIN_SAMPLES:
        return {"part": part, "n": len(prices)}
    prices.sort()
    return {"part": part, "n": len(prices), "min": prices[0],
            "median": round(statistics.median(prices)), "max": prices[-1]}


def verdict(our_price: float, stats: dict) -> str:
    if stats.get("n", 0) < MIN_SAMPLES:
        return f"мало данных по рынку ({stats.get('n', 0)} объявлений)"
    med = stats["median"]
    if our_price > med * 1.15:
        return f"выше рынка (медиана {med:.0f}) — можно снизить для скорости продажи"
    if our_price < med * 0.85:
        return f"ниже рынка (медиана {med:.0f}) — есть пространство поднять цену"
    return f"в рынке (медиана {med:.0f}, диапазон {stats['min']:.0f}–{stats['max']:.0f})"


def report() -> dict:
    out = []
    try:
        conn = sqlite3.connect(DB)
    except Exception:
        return {"status": "error", "rows": []}
    try:
        inv = json.loads((ROOT / "data" / "inventory.json").read_text(encoding="utf-8"))
    except Exception:
        inv = []
    for item in inv if isinstance(inv, list) else []:
        name = str(item.get("name") or "")
        price = float(item.get("price") or 0)
        if not name:
            continue
        stats = market_stats(name, conn)
        out.append({"name": name, "our_price": price, **stats,
                    "verdict": verdict(price, stats)})
    return {"status": "ok", "rows": out}


def main() -> int:
    print(json.dumps(report(), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
