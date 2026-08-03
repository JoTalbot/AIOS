"""Autonomy Report — сводки, алерты аномалий и рекомендации (самообучение).

Даёт владельцу:
  * daily_summary()   — сводка дня: авто/эскалации/блокировки/продажи.
  * anomalies()       — подозрительная активность (частые «ниже пола», эскалации).
  * floor_advice()    — рекомендации по ценовым полам (для подтверждения владельцем).
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from .journal import Journal
from .policy import AutonomyPolicy

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _load_inventory() -> list[dict]:
    try:
        return json.loads((PROJECT_ROOT / "data" / "inventory.json").read_text(encoding="utf-8"))
    except Exception:
        return []


def _load_finance() -> list[dict]:
    try:
        return json.loads((PROJECT_ROOT / "data" / "finance.json").read_text(encoding="utf-8"))
    except Exception:
        return []


def daily_summary(days: int = 1) -> dict:
    """Сводка по журналу автономии за последние N дней."""
    j = Journal()
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    rows = []
    try:
        if j.path.exists():
            for line in j.path.read_text(encoding="utf-8").splitlines():
                try:
                    r = json.loads(line)
                    if r.get("ts", "") >= since:
                        rows.append(r)
                except Exception:
                    continue
    except Exception:
        pass

    by_decision = Counter(r.get("decision", "?") for r in rows)
    by_action = Counter(r.get("action", "?") for r in rows)
    sales_rows = [r for r in rows if r.get("action") == "log_sale" and r.get("result") == "ok"]
    total_sales = 0.0
    for r in sales_rows:
        try:
            total_sales += float((r.get("params") or {}).get("amount", 0))
        except Exception:
            pass

    # по платформам
    by_platform = Counter(r.get("platform", "?") for r in rows)

    return {
        "days": days,
        "total_decisions": len(rows),
        "by_decision": dict(by_decision),
        "by_action": dict(by_action),
        "by_platform": dict(by_platform),
        "sales": len(sales_rows),
        "sales_amount": round(total_sales, 2),
    }


def anomalies(limit: int = 20) -> list[dict]:
    """Поиск аномалий: частые «ниже пола» от одного клиента, всплеск эскалаций."""
    j = Journal()
    rows = []
    try:
        if j.path.exists():
            for line in j.path.read_text(encoding="utf-8").splitlines():
                try:
                    rows.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        pass

    out = []
    # ниже пола / блокировки от одного чата
    per_chat = Counter()
    for r in rows:
        if r.get("reason") and "ниже пола" in str(r.get("reason", "")):
            key = f"{r.get('platform')}:{r.get('chat')}"
            per_chat[key] += 1
    for key, cnt in per_chat.items():
        if cnt >= 3:
            out.append({"type": "below_floor_repeat", "key": key, "count": cnt,
                        "note": f"клиент {key} неоднократно пытался торговать ниже пола"})
    # всплеск эскалаций
    esc = [r for r in rows if r.get("decision") in ("ESCALATE", "MANUAL")]
    if len(esc) >= 8:
        out.append({"type": "escalation_burst", "count": len(esc),
                    "note": "много решений вынесено на подтверждение владельца за последнее время"})
    return out[:limit]


def floor_advice() -> dict:
    """Рекомендации по ценовым полам на основе склада (для ручного подтверждения)."""
    inv = _load_inventory()
    fin = _load_finance()
    policy = AutonomyPolicy()
    current = policy.floors.get("items", {})
    advice = []

    for it in inv:
        name = (it.get("name") or "").strip()
        price = float(it.get("price") or 0)
        if not name or price <= 0:
            continue
        floor = current.get(name.lower()) or current.get(name)
        if floor is None:
            # предлагаем 90% от цены как начальный пол
            advice.append({"item": name, "price": price, "suggested_floor": round(price * 0.9),
                           "status": "no_floor"})
        else:
            advice.append({"item": name, "price": price, "current_floor": floor,
                           "status": "has_floor"})

    # продажи — какие товары реально уходили
    sold = Counter()
    for e in fin:
        if e.get("kind") == "sale" and e.get("desc"):
            sold[e["desc"]] += float(e.get("amount", 0))
    return {
        "items_without_floor": [a for a in advice if a["status"] == "no_floor"],
        "items_with_floor": [a for a in advice if a["status"] == "has_floor"],
        "recent_sales": [{"item": k, "amount": v} for k, v in sold.items()],
    }
