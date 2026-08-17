#!/usr/bin/env python3
"""Historical crypto news collector from Wayback Machine RSS snapshots.

Fetches CoinTelegraph RSS snapshots archived by the Internet Archive over the
last ~12 months (one snapshot every `step_hours`), extracts article titles with
their real publication dates (pubDate), dedupes by URL, writes
data/quant/news_historical.jsonl.

Usage:
    python scripts/fetch_historical_news.py [--step-hours 40] [--limit 250]
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path("/root/AIOS")
OUT = ROOT / "data" / "quant" / "news_historical.jsonl"
CDX = "http://web.archive.org/cdx/search/cdx"
FEED = "cointelegraph.com/rss"


def get(url: str, timeout: int = 40) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def list_snapshots() -> list[str]:
    url = f"{CDX}?url={FEED}&from=20250801&to=20260816&output=json"
    data = json.loads(get(url).decode())
    return [row[1] for row in data[1:]] if len(data) > 1 else []


def parse_rss(raw: bytes) -> list[dict]:
    items = []
    try:
        root = ET.fromstring(raw)
        for it in root.iter("item"):
            title = (it.findtext("title") or "").strip()
            link = (it.findtext("link") or "").strip()
            pub = (it.findtext("pubDate") or "").strip()
            if title:
                items.append({"title": title, "url": link, "pub": pub})
    except Exception:
        pass
    return items


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--step-hours", type=int, default=40)
    ap.add_argument("--limit", type=int, default=250)
    args = ap.parse_args()

    snaps = list_snapshots()
    print(f"снапшотов в архиве: {len(snaps)}", flush=True)

    # выбираем снапшоты с шагом step_hours (~ каждые N часов)
    selected = []
    last_ts = None
    for s in snaps:
        ts = datetime.strptime(s, "%Y%m%d%H%M%S").replace(tzinfo=UTC)
        if last_ts is None or (ts - last_ts) >= timedelta(hours=args.step_hours):
            selected.append((s, ts))
            last_ts = ts
    if args.limit:
        selected = selected[:args.limit]
    print(f"выбрано для скачивания: {len(selected)}", flush=True)

    seen_urls = set()
    if OUT.exists():
        for line in OUT.read_text().splitlines():
            try:
                seen_urls.add(json.loads(line)["url"])
            except Exception:
                pass

    fetched = 0
    for s, ts in selected:
        url = f"https://web.archive.org/web/{s}id_/{FEED}"
        try:
            raw = get(url)
            items = parse_rss(raw)
        except Exception as e:
            print(f"  {s} fail: {e}", flush=True)
            continue
        rows = []
        for it in items:
            if it["url"] in seen_urls:
                continue
            seen_urls.add(it["url"])
            rows.append({
                "ts": ts.timestamp(),
                "date": ts.strftime("%Y-%m-%d %H:%M"),
                "source": "cointelegraph_arch",
                "title": it["title"][:300],
                "url": it["url"],
                "pub": it["pub"],
                "snapshot": s,
            })
        if rows:
            with open(OUT, "a") as f:
                for r in rows:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            fetched += len(rows)
        time.sleep(0.6)

    total = sum(1 for _ in open(OUT)) if OUT.exists() else 0
    print(f"новых заголовков: {fetched}, всего в базе: {total}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
