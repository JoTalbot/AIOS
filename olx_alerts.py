"""OLX Alerts & Analytics.

Handles:
- Subscriptions (chat_ids per query) in SQLite
- New-ad detection between collection cycles
- Price analytics (min/max/avg/median/p10/p90) per query
- Sending Telegram alerts to subscribed chats
"""
from __future__ import annotations

import json
import logging
import sqlite3
import statistics
import urllib.request
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

log = logging.getLogger("olx-alerts")

DEFAULT_DB = "/root/AIOS/data/olx_http.sqlite"
SUBS_DB = "/root/AIOS/data/olx_subs.sqlite"
TG_API = "https://api.telegram.org/bot{token}/sendMessage"


# ---------------------------------------------------------------------------
# Subscription store
# ---------------------------------------------------------------------------
def init_subs_db(path: str = SUBS_DB) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS subscribers (
        chat_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        subscribed_at TEXT NOT NULL,
        enabled INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS subscriptions (
        chat_id INTEGER NOT NULL,
        query   TEXT NOT NULL,
        min_price REAL,
        max_price REAL,
        created_at TEXT NOT NULL,
        PRIMARY KEY (chat_id, query)
    );
    CREATE TABLE IF NOT EXISTS sent_alerts (
        chat_id INTEGER NOT NULL,
        ad_id INTEGER NOT NULL,
        query TEXT NOT NULL,
        sent_at TEXT NOT NULL,
        PRIMARY KEY (chat_id, ad_id)
    );
    CREATE INDEX IF NOT EXISTS idx_sent_query ON sent_alerts(query);
    """)
    conn.commit()
    return conn


def subscribe_chat(conn: sqlite3.Connection, chat_id: int, query: str,
                   username: str | None = None, first_name: str | None = None,
                   min_price: float | None = None, max_price: float | None = None):
    now = datetime.now(UTC).isoformat()
    conn.execute(
        "INSERT OR IGNORE INTO subscribers(chat_id,username,first_name,subscribed_at,enabled) "
        "VALUES (?,?,?,?,1)", (chat_id, username, first_name, now))
    conn.execute(
        "INSERT OR REPLACE INTO subscriptions(chat_id,query,min_price,max_price,created_at) "
        "VALUES (?,?,?,?,?)", (chat_id, query, min_price, max_price, now))
    conn.commit()


def unsubscribe_chat(conn: sqlite3.Connection, chat_id: int, query: str | None = None):
    if query:
        conn.execute("DELETE FROM subscriptions WHERE chat_id=? AND query=?", (chat_id, query))
    else:
        conn.execute("DELETE FROM subscriptions WHERE chat_id=?", (chat_id,))
    conn.commit()


def list_subscriptions(conn: sqlite3.Connection, chat_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT query, min_price, max_price, created_at FROM subscriptions "
        "WHERE chat_id=? ORDER BY query", (chat_id,)).fetchall()
    return [{"query": r[0], "min_price": r[1], "max_price": r[2], "created_at": r[3]} for r in rows]


def all_enabled_chats_for_query(conn: sqlite3.Connection, query: str) -> list[int]:
    rows = conn.execute(
        "SELECT s.chat_id FROM subscriptions s "
        "JOIN subscribers sub ON sub.chat_id=s.chat_id "
        "WHERE s.query=? AND sub.enabled=1", (query,)).fetchall()
    return [r[0] for r in rows]


def mark_sent(conn: sqlite3.Connection, chat_id: int, ad_id: int, query: str):
    conn.execute(
        "INSERT OR IGNORE INTO sent_alerts(chat_id,ad_id,query,sent_at) VALUES (?,?,?,?)",
        (chat_id, ad_id, query, datetime.now(UTC).isoformat()))
    conn.commit()


def already_sent(conn: sqlite3.Connection, chat_id: int, ad_id: int) -> bool:
    return conn.execute(
        "SELECT 1 FROM sent_alerts WHERE chat_id=? AND ad_id=?", (chat_id, ad_id)
    ).fetchone() is not None


# ---------------------------------------------------------------------------
# Price analytics
# ---------------------------------------------------------------------------
@dataclass
class PriceStats:
    query: str
    count: int
    min_p: float
    max_p: float
    avg: float
    median: float
    p10: float
    p90: float


def compute_price_stats(ads_conn: sqlite3.Connection, query: str) -> PriceStats | None:
    rows = ads_conn.execute(
        "SELECT price_value FROM ads WHERE query=? AND active=1 AND price_currency='UAH' "
        "AND price_value IS NOT NULL AND price_value > 0",
        (query,)).fetchall()
    vals = sorted(r[0] for r in rows)
    if not vals:
        return None
    def pct(p):
        if len(vals) == 1:
            return vals[0]
        k = (len(vals) - 1) * p
        f = int(k)
        c = min(f + 1, len(vals) - 1)
        return vals[f] + (vals[c] - vals[f]) * (k - f)
    return PriceStats(
        query=query, count=len(vals),
        min_p=vals[0], max_p=vals[-1],
        avg=statistics.fmean(vals),
        median=statistics.median(vals),
        p10=pct(0.10), p90=pct(0.90),
    )


def price_assessment(stats: PriceStats, price: float) -> str:
    """Return human-friendly tag + emoji for a price relative to market."""
    if price <= stats.p10:
        return "🔥🔥 СУПЕР ЦІНА (нижче ринку)"
    if price <= stats.median * 0.85:
        return "🔥 ДЕШЕВШЕ ринку"
    if price >= stats.p90:
        return "💸 ДОРОГО (вище ринку)"
    if price >= stats.median * 1.15:
        return "⚠️ ВИЩЕ середнього"
    if price <= stats.median * 0.95:
        return "✅ Трохи дешевше"
    return "➖ Нормальна ціна"


# ---------------------------------------------------------------------------
# New-ad detection (after a collection cycle)
# ---------------------------------------------------------------------------
def find_new_ads(ads_conn: sqlite3.Connection, since_ts: str, query: str,
                 min_price: float | None = None, max_price: float | None = None) -> list[dict]:
    """Return ads inserted or refreshed after since_ts that were never collected before."""
    sql = """
    SELECT a.* FROM ads a
    LEFT JOIN (
        -- ads that existed before since_ts (first collected earlier)
        SELECT id, MIN(collected_at) as first_seen FROM ads
        GROUP BY id
    ) old ON a.id=old.id
    WHERE a.query=? AND a.active=1
      AND (old.first_seen IS NULL OR old.first_seen >= ?)
    """
    params = [query, since_ts]
    if min_price is not None:
        sql += " AND (a.price_value IS NULL OR a.price_value >= ?)"
        params.append(min_price)
    if max_price is not None:
        sql += " AND (a.price_value IS NULL OR a.price_value <= ?)"
        params.append(max_price)
    sql += " ORDER BY a.promoted DESC, a.top_ad DESC, a.price_value IS NOT NULL, a.price_value ASC LIMIT 25"
    rows = ads_conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Telegram sending
# ---------------------------------------------------------------------------
def tg_send(token: str, chat_id: int, text: str, parse_mode: str = "HTML",
            disable_web_preview: bool = False) -> bool:
    url = TG_API.format(token=token)
    data = json.dumps({
        "chat_id": chat_id,
        "text": text[:4000],
        "parse_mode": parse_mode,
        "disable_web_page_preview": disable_web_preview,
    }).encode()
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            return bool(result.get("ok"))
    except Exception as e:
        log.warning("Telegram send failed to %s: %s", chat_id, e)
        return False


def format_ad_message(ad: dict, stats: PriceStats | None, query: str) -> str:
    price = ad.get("price_value")
    cur = ad.get("price_currency") or "грн"
    if price is None:
        price_str = "💵 Договірна"
    else:
        price_str = f"💵 <b>{int(price):,} {cur}</b>".replace(",", " ")
    tag = ""
    if stats and price is not None and cur == "UAH":
        tag = f" — {price_assessment(stats, price)}"
    title = (ad.get("title") or "(без назви)").replace("<", "&lt;").replace(">", "&gt;")
    city = ad.get("city") or "?"
    name = ad.get("user_name") or "?"
    is_business = "🏢" if ad.get("business") else "👤"
    url = ad.get("url") or "#"
    return (
        f"🔔 <b>Нове оголошення</b> «{query}»{tag}\n"
        f"<a href=\"{url}\">{title}</a>\n"
        f"{price_str}\n"
        f"📍 {city} · {is_business} {name}\n"
    )


def send_cycle_alerts(ads_conn: sqlite3.Connection, subs_conn: sqlite3.Connection,
                      tg_token: str, queries: Iterable[str], cycle_ts: str,
                      previous_cycle_ts: str | None, max_per_query_per_chat: int = 5):
    """Send new-ad alerts for every subscribed chat.

    previous_cycle_ts: last completed cycle's timestamp (cutoff for "newness").
    """
    for query in queries:
        stats = compute_price_stats(ads_conn, query)
        chats = all_enabled_chats_for_query(subs_conn, query)
        if not chats:
            continue
        # Get fresh ads since previous_cycle
        new_ads = find_new_ads(ads_conn, previous_cycle_ts or cycle_ts, query)
        if not new_ads:
            continue
        log.info("Alerts for '%s': %d new ads, %d subscribed chats",
                 query, len(new_ads), len(chats))
        for chat_id in chats:
            sent = 0
            # Determine price filter for this chat+query
            sub = subs_conn.execute(
                "SELECT min_price, max_price FROM subscriptions WHERE chat_id=? AND query=?",
                (chat_id, query)).fetchone()
            min_p, max_p = (sub[0], sub[1]) if sub else (None, None)
            filtered = [
                a for a in new_ads
                if (min_p is None or a.get("price_value") is None or a["price_value"] >= min_p)
                and (max_p is None or a.get("price_value") is None or a["price_value"] <= max_p)
                and not already_sent(subs_conn, chat_id, a["id"])
            ]
            for ad in filtered[:max_per_query_per_chat]:
                text = format_ad_message(ad, stats, query)
                if tg_send(tg_token, chat_id, text, disable_web_preview=False):
                    mark_sent(subs_conn, chat_id, ad["id"], query)
                    sent += 1
                else:
                    break
            if sent:
                log.info("  sent %d alerts to chat %d", sent, chat_id)
