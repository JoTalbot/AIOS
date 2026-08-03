#!/usr/bin/env python3
"""
AIOS Price Guide — «сколько стоит <деталь>?»: ищет похожие объявления в OLX-БД,
считает медиану/диапазон, и через LLM даёт оценку цены.
  python run_price_guide.py "<запрос>"
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ADS_DB = ROOT / "data" / "olx_http.sqlite"


def _env(key: str) -> str:
    import os
    v = os.environ.get(key, "")
    if v:
        return v
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _llm(prompt: str) -> str:
    import urllib.request as _urllib
    _b = None
    try:
        from aios_core.llm_balancer import LLMBalancer as _LB
        _b = _LB()
    except Exception:
        _b = None
    if _b is not None:
        try:
            r = _b.chat([{"role": "user", "content": prompt}],
                        model=_env("LLM_MODEL") or "meta-llama/llama-4-maverick",
                        system="Ты эксперт по ценам на автозапчасти в Украине. Отвечай кратко, по-русски.",
                        max_tokens=300, temperature=0.3, task_type="chat")
            if r:
                return r
        except Exception:
            pass
    try:
        key = _env("OPENROUTER_API_KEY")
        if key:
            payload = json.dumps({
                "model": "mistralai/mistral-small-3.2-24b-instruct",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 300, "temperature": 0.3,
            }).encode()
            req = _urllib.Request("https://openrouter.ai/api/v1/chat/completions",
                                  data=payload, headers={
                                      "Content-Type": "application/json",
                                      "Authorization": "Bearer " + key})
            with _urllib.urlopen(req, timeout=60) as resp:
                d = json.loads(resp.read())
            return d["choices"][0]["message"]["content"]
    except Exception:
        pass
    return ""


def _similar(query: str, limit: int = 30) -> list[dict]:
    """Найти похожие объявления в OLX-БД (по словам запроса)."""
    try:
        conn = sqlite3.connect(str(ADS_DB))
    except Exception:
        return []
    words = [w for w in query.lower().split() if len(w) > 2]
    if not words:
        return []
    where = " AND ".join(["(LOWER(title) LIKE ? OR LOWER(description) LIKE ?)"] * len(words))
    params = []
    for w in words:
        params += [f"%{w}%", f"%{w}%"]
    try:
        rows = conn.execute(
            f"SELECT title, price_value, price_currency, city, url FROM ads "
            f"WHERE active = 1 AND price_value > 0 AND ({where}) "
            f"ORDER BY collected_at DESC LIMIT {limit}", params).fetchall()
    except Exception:
        rows = []
    conn.close()
    return [{"title": r[0], "price": r[1], "cur": r[2], "city": r[3], "url": r[4]} for r in rows]


def price_guide(query: str) -> dict:
    """Оценка цены по запросу."""
    similar = _similar(query)
    prices = [s["price"] for s in similar]
    result = {"status": "ok", "query": query, "found": len(similar)}

    if prices:
        prices_sorted = sorted(prices)
        n = len(prices_sorted)
        median = prices_sorted[n // 2] if n % 2 else (prices_sorted[n // 2 - 1] + prices_sorted[n // 2]) / 2
        result["median"] = round(median)
        result["min"] = prices_sorted[0]
        result["max"] = prices_sorted[-1]
        result["examples"] = similar[:5]
        # LLM-оценка
        examples_txt = "\n".join(f"{s['title'][:60]} — {s['price']} грн ({s.get('city','')})" for s in similar[:8])
        prompt = (
            f"Найденные похожие объявления на OLX по запросу «{query}»:\n{examples_txt}\n\n"
            "Оцени: 1) реалистичную цену продажи такой детали в Украине (одно число в грн), "
            "2) краткий комментарий (1-2 предложения): на что смотреть (состояние, год, комплектация). "
            "Формат: «Цена: ~X грн. Комментарий: ...»"
        )
        llm = _llm(prompt)
        if llm:
            result["ai_advice"] = llm.strip()
    else:
        result["note"] = "Похожих объявлений в базе нет."
    return result


def main() -> None:
    query = " ".join(sys.argv[1:])
    if not query:
        print(json.dumps({"status": "error", "error": "Укажите запрос"}))
        return
    print(json.dumps(price_guide(query), ensure_ascii=False))


if __name__ == "__main__":
    main()
