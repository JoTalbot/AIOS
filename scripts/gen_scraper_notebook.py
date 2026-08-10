#!/usr/bin/env python3
"""AIOS - Генератор ноутбука Scraper Farm (Этап 5)."""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path("/root/AIOS")
DOCS = REPO / "docs"


def md(s: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": s.splitlines(keepends=True)}


def code(s: str) -> dict:
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": s.splitlines(keepends=True)}


def base_meta():
    return {"colab": {"provenance": []}, "kernelspec": {"name": "python3", "display_name": "Python 3"},
            "language_info": {"name": "python"}}


def nb() -> dict:
    cells = [
        md(
            "# 🕷️ AIOS Scraper Farm (Playwright)\n\n"
            "Высокоскоростной скрапинг с **чистых IP Google** через гигабитный канал Colab.\n"
            "Мониторинг: аирдропы, CryptoPanic, Freelancehunt, DEX-пулы, новости.\n\n"
            "Задания можно создавать на VPS: `python scripts/dispatch_colab_scrape.py create ...`.\n\n"
            "Результаты сохраняются в файл и переносятся на VPS для ингеста (`result_ingest.py`)."
        ),
        code("!pip install -q playwright pandas\n"
             "!playwright install chromium\n"
             "from playwright.sync_api import sync_playwright\n"
             "import json, re\n"
             "print('✅ Playwright установлен')"),
        code("# === ЯЧЕЙКА 2: Конфигурация задачи ===\n"
             "JOB = {\n"
             "    'source': 'cryptopanic',   # airdrops | cryptopanic | freelancehunt | dex | news\n"
             "    'urls': ['https://cryptopanic.com/news/'],\n"
             "    'max_pages': 2,\n"
             "}\n"
             "print('Задание:', JOB)"),
        code("# === ЯЧЕЙКА 3: Скрапинг через Playwright ===\n"
             "results = []\n"
             "with sync_playwright() as p:\n"
             "    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])\n"
             "    page = browser.new_page()\n"
             "    for url in JOB['urls']:\n"
             "        page.goto(url, wait_until='domcontentloaded', timeout=60000)\n"
             "        page.wait_for_timeout(3000)\n"
             "        items = page.eval_on_selector_all(\n"
             "            'a, h1, h2, h3, article, .title, [class*=title]',\n"
             "            \"\"\"els => els.slice(0,60).map(e => ({\n"
             "                tag: e.tagName,\n"
             "                text: (e.innerText||'').trim().slice(0,250),\n"
             "                href: e.href||''\n"
             "            }))\"\"\")\n"
             "        results.extend(items)\n"
             "    browser.close()\n"
             "print('✅ Собрано элементов:', len(results))"),
        code("# === ЯЧЕЙКА 4: Нормализация и сохранение ===\n"
             "norm = []\n"
             "seen = set()\n"
             "for it in results:\n"
             "    t = (it.get('text') or '').strip()\n"
             "    if not t or len(t) < 5:\n"
             "        continue\n"
             "    key = (it.get('href') or t)\n"
             "    if key in seen:\n"
             "        continue\n"
             "    seen.add(key)\n"
             "    norm.append({'source': JOB['source'], 'title': t, 'url': it.get('href')})\n"
             "print('Нормализовано:', len(norm))\n"
             "\n"
             "with open('scrape_results.json', 'w', encoding='utf-8') as f:\n"
             "    json.dump(norm, f, ensure_ascii=False, indent=2)\n"
             "print('✅ Сохранено: scrape_results.json')\n"
             "print('Скачайте файл на VPS и запустите:')\n"
             "print('  python scripts/dispatch_colab_scrape.py create --source <SOURCE> --target <URL>')\n"
             "print('  python aios_core/scraping/result_ingest.py --source <SOURCE> --input scrape_results.json')"),
    ]
    return {"cells": cells, "metadata": base_meta(), "nbformat": 4, "nbformat_minor": 0}


if __name__ == "__main__":
    p = DOCS / "AIOS_Colab_Scraper_Farm.ipynb"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(nb(), indent=1), encoding="utf-8")
    print(f"✅ {p} ({p.stat().st_size} байт)")
