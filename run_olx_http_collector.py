"""AIOS OLX HTTP Collector — permanent collection via public OLX API + Telegram alerts.

Fast, emulator-independent, uses https://www.olx.ua/api/v1/offers/
Emulator stays reserved for interactive tasks (login/posting/chats).
"""

import argparse
import json
import logging
import os
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
import urllib.parse

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

API = "https://www.olx.ua/api/v1/offers/"

HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "uk-UA,uk;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Referer": "https://www.olx.ua/",
}
log = logging.getLogger("olx-http-collector")


def init_db(path: str) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("""
    CREATE TABLE IF NOT EXISTS ads (
        id INTEGER PRIMARY KEY,
        query TEXT NOT NULL,
        url TEXT,
        title TEXT,
        price_value REAL,
        price_currency TEXT,
        price_label TEXT,
        negotiable INTEGER DEFAULT 0,
        city TEXT,
        region TEXT,
        description TEXT,
        category TEXT,
        photos_json TEXT,
        user_id INTEGER,
        user_name TEXT,
        business INTEGER DEFAULT 0,
        is_new INTEGER DEFAULT 0,
        promoted INTEGER DEFAULT 0,
        urgent INTEGER DEFAULT 0,
        top_ad INTEGER DEFAULT 0,
        created_time TEXT,
        last_refresh_time TEXT,
        first_seen TEXT,
        collected_at TEXT NOT NULL,
        active INTEGER DEFAULT 1
    )""")
    # Migration: add first_seen if missing on existing DBs
    cols = [r[1] for r in conn.execute("PRAGMA table_info(ads)")]
    if "first_seen" not in cols:
        conn.execute("ALTER TABLE ads ADD COLUMN first_seen TEXT")
        conn.execute("UPDATE ads SET first_seen = collected_at WHERE first_seen IS NULL")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ads_query ON ads(query)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ads_collected ON ads(collected_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ads_active ON ads(active)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ads_first ON ads(first_seen)")
    conn.commit()
    return conn


def extract_price(offer: dict):
    for p in offer.get("params", []):
        if p.get("key") == "price":
            v = p.get("value") or {}
            return (v.get("value"), v.get("currency"), v.get("label"), 1 if v.get("negotiable") else 0)
    return (None, None, None, 0)


def parse_offer(offer: dict, query: str, is_new_ad: bool) -> tuple:
    price, cur, label, neg = extract_price(offer)
    loc = offer.get("location") or {}
    city = loc.get("city", {}).get("name") if isinstance(loc.get("city"), dict) else loc.get("city")
    region = loc.get("region", {}).get("name") if isinstance(loc.get("region"), dict) else loc.get("region")
    user = offer.get("user") or {}
    promo = offer.get("promotion") or {}
    now = datetime.now(timezone.utc).isoformat()
    return (
        offer["id"],
        query,
        offer.get("url"),
        offer.get("title"),
        price,
        cur,
        label,
        neg,
        city,
        region,
        re.sub(r"<[^>]+>", " ", offer.get("description") or ""),
        (offer.get("category") or {}).get("type") if offer.get("category") else None,
        json.dumps([ph.get("link", "") for ph in (offer.get("photos") or [])[:10]]),
        user.get("id"),
        user.get("name"),
        1 if offer.get("business") else 0,
        1 if offer.get("offer_type") == "new" else 0,
        1 if promo.get("highlighted") else 0,
        1 if promo.get("urgent") else 0,
        1 if promo.get("top_ad") else 0,
        offer.get("created_time"),
        offer.get("last_refresh_time"),
        now if is_new_ad else None,  # first_seen
        now,  # collected_at
    )


def fetch_page(client: httpx.Client, query: str, offset: int, limit: int = 50, max_retries: int = 3) -> dict:
    """Fetch OLX page with retry and exponential backoff."""
    import time, random
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                delay = (2 ** attempt) + random.uniform(0, 1)
                log.info(f"Retry {attempt}/{max_retries}, waiting {delay:.1f}s...")
                time.sleep(delay)
            
            import subprocess as _sp
            import json as _json
            _url = API + "?" + "&".join(
                f"{k}={urllib.parse.quote(str(v))}"
                for k, v in [("query", query), ("offset", offset), ("limit", limit)]
            )
            _cur = _sp.run(
                ["curl", "-s", "-m", "25", "-A", UA, "-H", "Referer: https://www.olx.ua/",
                 "-H", "Accept: application/json, text/plain, */*", _url],
                capture_output=True, text=True,
            )
            if _cur.returncode != 0 or not _cur.stdout.strip():
                raise httpx.HTTPStatusError("curl failed/empty", request=None, response=type("R", (), {"status_code": 502})())
            _data = _json.loads(_cur.stdout)
            return _data

        except httpx.HTTPStatusError as e:
            if attempt == max_retries - 1:
                raise
            log.warning(f"HTTP error (attempt {attempt + 1}/{max_retries}): {e}")
            continue
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            log.warning(f"Error (attempt {attempt + 1}/{max_retries}): {e}")
            continue
    
    return {}


def cycle(client: httpx.Client, conn: sqlite3.Connection, queries: list[str], max_cards_per_query: int = 300) -> dict:
    stats = {"parsed": 0, "inserted": 0, "deactivated": 0, "new_ads": 0}
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    new_ad_ids: set[int] = set()
    for q in queries:
        log.info("=== Query: %s ===", q)
        seen: set[int] = set()
        query_new = 0
        total_inserted = 0
        offset = 0
        while len(seen) < max_cards_per_query:
            try:
                data = fetch_page(client, q, offset=offset, limit=50)
            except Exception as e:
                log.exception("HTTP error: %s", e)
                break
            offers = data.get("data") or []
            if not offers:
                break
            rows = []
            page_new = 0
            for off in offers:
                oid = off["id"]
                if oid in seen:
                    continue
                seen.add(oid)
                # Check if ad is brand-new to DB
                existing = cur.execute("SELECT 1 FROM ads WHERE id=?", (oid,)).fetchone()
                is_new = existing is None
                if is_new:
                    new_ad_ids.add(oid)
                    page_new += 1
                rows.append(parse_offer(off, q, is_new))
            if rows:
                cur.executemany(
                    """INSERT INTO ads
                    (id,query,url,title,price_value,price_currency,price_label,negotiable,
                     city,region,description,category,photos_json,user_id,user_name,
                     business,is_new,promoted,urgent,top_ad,created_time,last_refresh_time,
                     first_seen,collected_at,active)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)
                    ON CONFLICT(id) DO UPDATE SET
                        query=excluded.query,
                        url=excluded.url,
                        title=excluded.title,
                        price_value=excluded.price_value,
                        price_currency=excluded.price_currency,
                        price_label=excluded.price_label,
                        negotiable=excluded.negotiable,
                        city=excluded.city,
                        region=excluded.region,
                        description=excluded.description,
                        category=excluded.category,
                        photos_json=excluded.photos_json,
                        user_id=excluded.user_id,
                        user_name=excluded.user_name,
                        business=excluded.business,
                        is_new=excluded.is_new,
                        promoted=excluded.promoted,
                        urgent=excluded.urgent,
                        top_ad=excluded.top_ad,
                        created_time=excluded.created_time,
                        last_refresh_time=excluded.last_refresh_time,
                        collected_at=excluded.collected_at,
                        active=1
                    """,
                    rows,
                )
                conn.commit()
                # executemany rowcount is unreliable across sqlite versions; count new ads by len of new-set delta
                total_inserted += len(rows)
                query_new += page_new
            offset += len(offers)
            total = data.get("metadata", {}).get("total_elements")
            if offset >= (total or offset + 1):
                break
            time.sleep(1.0)
        # Mark not-seen ads for this query as inactive
        if seen:
            cur.execute(
                f"UPDATE ads SET active=0 WHERE query=? AND id NOT IN ({','.join('?' * len(seen))})",
                [q, *list(seen)],
            )
            conn.commit()
            deact = cur.rowcount
        else:
            deact = 0
        log.info("   collected=%d, updated=%d, new=%d, deactivated=%d", len(seen), total_inserted, query_new, deact)
        stats["parsed"] += len(seen)
        stats["inserted"] += total_inserted
        stats["deactivated"] += deact
        time.sleep(1.5)
    stats["new_ads"] = len(new_ad_ids)
    cur.execute(
        "INSERT INTO collection_runs(ts,queries,parsed,inserted,deactivated) VALUES (?,?,?,?,?)",
        (now, json.dumps(queries), stats["parsed"], stats["inserted"], stats["deactivated"]),
    )
    conn.commit()
    stats["cycle_ts"] = now
    return stats


def main():
    ap = argparse.ArgumentParser(description="AIOS OLX HTTP Collector")
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=int, default=1800)
    ap.add_argument("--db", default=os.environ.get("AIOS_OLX_HTTP_DB", "/root/AIOS/data/olx_http.sqlite"))
    ap.add_argument("--max-cards", type=int, default=300)
    ap.add_argument("--no-alerts", action="store_true", help="Do not send Telegram alerts even if token is set")
    ap.add_argument(
        "--queries",
        nargs="+",
        default=[
            "iPhone",
            "PlayStation 5",
            "квартира Київ",
            "RTX 4090",
            "MacBook",
            "Galaxy S24",
            "авто бу",
            "велосипед",
            "дитячі речі",
            "робота Київ",
        ],
    )
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler("/root/AIOS/logs/olx_collector.log"), logging.StreamHandler(sys.stdout)],
    )
    Path("/root/AIOS/logs").mkdir(parents=True, exist_ok=True)

    # Ensure runs meta table exists
    init_meta = sqlite3.connect(args.db)
    init_meta.execute("""
        CREATE TABLE IF NOT EXISTS collection_runs(
            ts TEXT PRIMARY KEY, queries TEXT, parsed INT, inserted INT, deactivated INT)
    """)
    init_meta.commit()
    init_meta.close()

    conn = init_db(args.db)

    # Lazy import alerts
    from tg_bot.credentials import secret_from_env_or_credential
    tg_token = secret_from_env_or_credential("AIOS_TELEGRAM_TOKEN", "TELEGRAM_BOT_TOKEN", credential="telegram_token")
    alerts_module = None
    subs_conn = None
    if tg_token and not args.no_alerts:
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import olx_alerts

            alerts_module = olx_alerts
            subs_conn = olx_alerts.init_subs_db()
            log.info("Telegram alerts enabled (subs db ready)")
        except Exception as e:
            log.warning("Alerts init failed: %s", e)
            alerts_module = None

    with httpx.Client(headers=HEADERS) as client:
        log.info(
            "Starting OLX collector (daemon=%s interval=%ss queries=%s max_cards=%d db=%s)",
            args.daemon,
            args.interval,
            args.queries,
            args.max_cards,
            args.db,
        )
        previous_cycle_ts = None
        if args.once or not args.daemon:
            s = cycle(client, conn, args.queries, args.max_cards)
            print(json.dumps(s, indent=2, ensure_ascii=False))
            if alerts_module and subs_conn and tg_token:
                alerts_module.send_cycle_alerts(
                    conn, subs_conn, tg_token, args.queries, s["cycle_ts"], previous_cycle_ts
                )
            return
        while True:
            try:
                s = cycle(client, conn, args.queries, args.max_cards)
                if alerts_module and subs_conn and tg_token:
                    try:
                        alerts_module.send_cycle_alerts(
                            conn, subs_conn, tg_token, args.queries, s["cycle_ts"], previous_cycle_ts
                        )
                    except Exception as e:
                        log.exception("Alerts failed: %s", e)
                previous_cycle_ts = s["cycle_ts"]
            except Exception as e:
                log.exception("Cycle failed: %s", e)
            log.info("Sleeping %ds...", args.interval)
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
