#!/usr/bin/env python3
"""Переоценка позиций ниже рынка на основе competitor_monitor.json.

Правило (консервативное):
  - n >= 2:  new_price = round((our + market_median) / 2), не выше our*3
  - n == 1:  new_price = round(our * 1.5)
Старые цены сохраняются в data/reprice_history.json.
"""
import json
from datetime import datetime
from pathlib import Path

ROOT = Path("/root/AIOS")
INV = ROOT / "data" / "inventory.json"
MON = ROOT / "data" / "competitor_monitor.json"
HIST = ROOT / "data" / "reprice_history.json"


def main() -> None:
    items = json.loads(INV.read_text(encoding="utf-8"))
    mon = json.loads(MON.read_text(encoding="utf-8"))
    by_name = {i["name"].strip().casefold(): i for i in mon["items"]}

    changes = []
    for it in items:
        name = it.get("name", "")
        key = name.strip().casefold()
        m = by_name.get(key)
        if not m or m["position"] != "below_market" or not m["market_median"]:
            continue
        our = float(it.get("price", 0))
        median = float(m["market_median"])
        n = int(m["competitors"])
        if our <= 0:
            continue
        if n >= 2:
            new_price = round((our + median) / 2)
            new_price = min(new_price, our * 3)
        else:
            new_price = round(our * 1.5)
        if new_price <= our:
            continue
        changes.append({
            "name": name,
            "old_price": our,
            "new_price": new_price,
            "market_min": m["market_min"],
            "market_median": median,
            "market_max": m["market_max"],
            "competitors": n,
        })
        it["price"] = float(new_price)

    INV.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

    hist = []
    if HIST.exists():
        try:
            hist = json.loads(HIST.read_text(encoding="utf-8"))
        except Exception:
            hist = []
    hist.append({"at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "changes": changes})
    HIST.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Переоценено позиций: {len(changes)}")
    for c in changes:
        print(f"  {c['name'][:48]:<50} {c['old_price']:.0f} -> {c['new_price']:.0f} грн (рынок {c['market_min']:.0f}-{c['market_max']:.0f})")


if __name__ == "__main__":
    main()
