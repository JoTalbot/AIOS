#!/usr/bin/env python3
"""
AIOS Scraper Farm - Диспетчер заданий скрапинга (Этап 5)

Два режима:
  1. --create   : создаёт задание в очереди data/scraping/ (для Colab-ноды).
  2. --run      : выполняет задание ЛОКАЛЬНО на VPS через Playwright (headless)
                  и ингестит результат. Colab используется для тяжёлых/чистых IP.

Использование:
    python scripts/dispatch_colab_scrape.py create --source airdrops --target https://airdrops.io/ --max-pages 2
    python scripts/dispatch_colab_scrape.py run --url https://example.com --source news
"""

from __future__ import annotations

import sys
import json
import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aios_core.scraping.job_spec import make_job, save_job, mark  # noqa: E402


def cmd_create(source: str, target: str, collect, max_pages: int) -> None:
    job = make_job(source=source, target=target, collect=collect, params={"max_pages": max_pages})
    path = save_job(job)
    print(f"✅ Задание создано: {path}")
    print(json.dumps(job, indent=2, ensure_ascii=False))


def cmd_run(url: str, source: str, max_pages: int = 1, collect=None, no_rag: bool = False) -> None:
    """Локальный скрапер через Playwright (headless chromium)."""
    from playwright.sync_api import sync_playwright

    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(accept_downloads=False)
        for i in range(max_pages):
            u = url if i == 0 else f"{url}?page={i+1}"
            print(f"→ {u}")
            page.goto(u, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(2000)
            # собираем ссылки + заголовки
            items = page.eval_on_selector_all(
                "a, h1, h2, h3, article",
                """els => els.slice(0,40).map(e => ({
                    tag: e.tagName,
                    text: (e.innerText||'').trim().slice(0,200),
                    href: e.href||''
                }))""")
            results.extend(items)
        browser.close()

    # нормализация
    normalized = []
    for it in results:
        if it.get("text"):
            normalized.append({"title": it["text"], "url": it.get("href")})
    print(f"Собрано элементов: {len(normalized)}")

    from aios_core.scraping.result_ingest import ingest_results
    res = ingest_results(normalized, source=source, to_rag=not no_rag)
    print(json.dumps(res, indent=2, ensure_ascii=False))


def main() -> int:
    ap = argparse.ArgumentParser(description="AIOS Scraper Farm Dispatcher")
    sub = ap.add_subparsers(dest="command", required=True)

    p_c = sub.add_parser("create")
    p_c.add_argument("--source", required=True)
    p_c.add_argument("--target", required=True)
    p_c.add_argument("--collect", nargs="*", default=None)
    p_c.add_argument("--max-pages", type=int, default=1)

    p_r = sub.add_parser("run")
    p_r.add_argument("--url", required=True)
    p_r.add_argument("--source", required=True)
    p_r.add_argument("--max-pages", type=int, default=1)
    p_r.add_argument("--collect", nargs="*", default=None)
    p_r.add_argument("--no-rag", action="store_true")

    args = ap.parse_args()
    if args.command == "create":
        cmd_create(args.source, args.target, args.collect, args.max_pages)
    else:
        cmd_run(args.url, args.source, args.max_pages, args.collect, args.no_rag)
    return 0


if __name__ == "__main__":
    sys.exit(main())
