"""AIOS Paid API v2.0 — v22 «Platform» groundwork.

Коммерческие endpoint'ы поверх APIMonetizationManager:
  GET  /api/v2/mon/products          — каталог продуктов и цены (free)
  GET  /api/v2/mon/olx-price?query=  — OLX Price Intelligence ($0.10)
  POST /api/v2/mon/code-audit        — ИИ-аудит кода ($0.10, внутри менеджера)
  POST /api/v2/mon/summarize         — суммаризация текста ($0.05, внутри менеджера)
  GET  /api/v2/mon/balance           — баланс и счётчики клиента (free)

Auth: заголовок X-API-Key (или ?api_key=). Списание — через APIMonetizationManager.
OLX-база резолвится: $AIOS_OLX_LIVE_DB → /app/hostdata/olx_http.sqlite (docker)
→ /root/AIOS/data/olx_http.sqlite (host). Read-only.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import statistics
import time
import threading
from typing import Any, Dict, List, Optional

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

logger = logging.getLogger("AIOS.API.Monetization")

OLX_PRICE_COST_USD = 0.10

PRODUCTS_CATALOG = {
    "olx_price_intel": {
        "cost_usd": OLX_PRICE_COST_USD,
        "method": "GET", "path": "/api/v2/mon/olx-price?query=<строка>",
        "desc": "OLX Price Intelligence: статистика цен (min/avg/median/max) по базе автозапчастей "
                "(1780+ живых объявлений, коллектор каждый час). Для автоназборок и реселлеров.",
    },
    "code_audit": {
        "cost_usd": 0.10,
        "method": "POST", "path": "/api/v2/mon/code-audit",
        "desc": "ИИ-аудит безопасности/PEP8 Python-кода. Body: {\"code\": \"...\"}",
    },
    "summarize": {
        "cost_usd": 0.05,
        "method": "POST", "path": "/api/v2/mon/summarize",
        "desc": "Экспресс-суммаризация текста, извлечение тезисов. Body: {\"text\": \"...\"}",
    },
}

_manager = None
_manager_lock = threading.Lock()

# v22-B: per-key token bucket rate limit (защита платных endpoint'ов)
_RATE_RPM = float(os.environ.get("AIOS_MON_RATE_LIMIT_RPM", "30"))  # запросов в минуту на ключ
_buckets: Dict[str, List[float]] = {}
_buckets_lock = threading.Lock()


def _rate_ok(key: str) -> bool:
    """Token bucket: capacity/refill = _RATE_RPM в минуту. False -> 429."""
    if _RATE_RPM <= 0:
        return True
    now = time.time()
    refill_per_sec = _RATE_RPM / 60.0
    with _buckets_lock:
        tokens, last = _buckets.get(key, (_RATE_RPM, now))
        tokens = min(_RATE_RPM, tokens + (now - last) * refill_per_sec)
        if tokens < 1.0:
            _buckets[key] = (tokens, now)
            return False
        _buckets[key] = (tokens - 1.0, now)
        return True


def _mgr():
    global _manager
    with _manager_lock:
        if _manager is None:
            from aios_core.api_monetization import APIMonetizationManager
            _manager = APIMonetizationManager()
    return _manager


def _key(request: Request) -> str:
    return request.headers.get("X-API-Key") or request.query_params.get("api_key") or ""


def _olx_db_path() -> Optional[str]:
    for p in (os.environ.get("AIOS_OLX_LIVE_DB"),
              "/app/hostdata/olx_http.sqlite",
              "/root/AIOS/data/olx_http.sqlite"):
        if p and os.path.exists(p):
            return p
    return None


def olx_price_intel(query: str, limit: int = 5) -> Dict[str, Any]:
    """Статистика цен по собранной базе OLX ads (LIKE по query/title объявлений)."""
    db = _olx_db_path()
    if not db:
        return {"status": "error", "error": "OLX database not available"}
    q = (query or "").strip()
    if not q:
        return {"status": "error", "error": "query is empty"}
    rows: List = []
    total = 0
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            cur = con.cursor()
            cand = cur.execute(
                "SELECT query, title, price_value, price_currency, city, url FROM ads "
                "WHERE price_value IS NOT NULL AND price_value > 0").fetchall()
            total = cur.execute("SELECT COUNT(*) FROM ads").fetchone()[0]
        finally:
            con.close()
    except Exception as e:
        return {"status": "error", "error": f"olx db read failed: {e}"}
    # SQLite LIKE/lower() регистронезависимы только для ASCII — кириллицу
    # сравниваем в Python через casefold (иначе «радиатор» ≠ «Радиатор»)
    qf = q.casefold()
    rows = [(r[1], r[2], r[3], r[4], r[5]) for r in cand
            if qf in str(r[0] or "").casefold() or qf in str(r[1] or "").casefold()]
    prices = [float(r[1]) for r in rows]
    if not prices:
        return {"status": "ok", "query": q, "matches": 0, "db_ads_total": total, "stats": None, "samples": []}
    stats = {
        "count": len(prices),
        "min": round(min(prices), 2),
        "max": round(max(prices), 2),
        "avg": round(sum(prices) / len(prices), 2),
        "median": round(statistics.median(prices), 2),
        "currency": rows[0][2] or "UAH",
    }
    samples = [{"title": r[0], "price": r[1], "city": r[3], "url": r[4]} for r in rows[:limit]]
    return {"status": "ok", "query": q, "matches": len(prices), "db_ads_total": total,
            "stats": stats, "samples": samples}


async def mon_products(request: Request) -> JSONResponse:
    return JSONResponse({
        "status": "ok",
        "products": PRODUCTS_CATALOG,
        "how_to_pay": "Депозит USDT (TRC20/EVM) → ключ у оператора; баланс: /api/v2/mon/balance?api_key=KEY",
        "wallet_trc20": "из .env AIOS (см. docs/PLATFORM_V22.md)",
    })


async def mon_olx_price(request: Request) -> JSONResponse:
    key = _key(request)
    if not _rate_ok(key):
        return JSONResponse({"status": "error", "error": "rate limit exceeded",
                             "limit": f"{_RATE_RPM:g} req/min per key"}, status_code=429)
    if not _mgr().verify_and_charge(key, OLX_PRICE_COST_USD, product="olx_price"):
        return JSONResponse({
            "status": "error",
            "error": "invalid or unpaid api key",
            "hint": "GET /api/v2/mon/products для каталога и способа оплаты",
        }, status_code=402)
    q = request.query_params.get("query", "")
    res = olx_price_intel(q)
    res["charged_usd"] = OLX_PRICE_COST_USD
    return JSONResponse(res)


async def mon_code_audit(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        body = {}
    code = str(body.get("code") or "")
    if not code.strip():
        return JSONResponse({"status": "error", "error": "body.code is empty"}, status_code=400)
    if not _rate_ok(_key(request)):
        return JSONResponse({"status": "error", "error": "rate limit exceeded"}, status_code=429)
    res = _mgr().process_code_audit(api_key=_key(request), code_snippet=code)
    status = 200 if res.get("status") == "success" else 402
    return JSONResponse(res, status_code=status)


async def mon_summarize(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        body = {}
    text = str(body.get("text") or "")
    if not text.strip():
        return JSONResponse({"status": "error", "error": "body.text is empty"}, status_code=400)
    if not _rate_ok(_key(request)):
        return JSONResponse({"status": "error", "error": "rate limit exceeded"}, status_code=429)
    res = _mgr().process_text_summarization(api_key=_key(request), text=text)
    status = 200 if res.get("status") == "success" else 402
    return JSONResponse(res, status_code=status)


async def mon_balance(request: Request) -> JSONResponse:
    key = _key(request)
    info = _mgr().load_keys().get(key)
    if not info:
        return JSONResponse({"status": "error", "error": "unknown api key"}, status_code=404)
    return JSONResponse({
        "status": "ok",
        "client_name": info.get("client_name"),
        "credits_usd": round(float(info.get("credits_usd", 0.0)), 4),
        "total_requests": info.get("total_requests", 0),
        "created_at": info.get("created_at"),
    })


def get_monetization_routes() -> List[Route]:
    return [
        Route("/api/v2/mon/products", mon_products, methods=["GET"]),
        Route("/api/v2/mon/olx-price", mon_olx_price, methods=["GET"]),
        Route("/api/v2/mon/code-audit", mon_code_audit, methods=["POST"]),
        Route("/api/v2/mon/summarize", mon_summarize, methods=["POST"]),
        Route("/api/v2/mon/balance", mon_balance, methods=["GET"]),
    ]
