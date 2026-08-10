#!/usr/bin/env python3
"""
AIOS Colab Probe - проверка доступа к Google Colab через CDP 9222.

Открывает colab.research.google.com, проверяет:
  - загрузилась ли страница,
  - авторизован ли аккаунт Google,
  - видит ли страница кнопки подключения.

Запуск:
    python scripts/colab_probe.py
"""

from __future__ import annotations

import sys
import json
import asyncio
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
os.environ["DISPLAY"] = os.environ.get("DISPLAY", ":1")

CDP_URL = "http://localhost:9222"


async def probe():
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
        from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await context.new_page()
        await page.set_viewport_size({"width": 1600, "height": 1000})

        url = "https://colab.research.google.com/?logout=false"
        print("🔗 Открываю Google Colab...")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(8)

        title = await page.title()
        content_url = page.url
        print("Title:", title)
        print("URL:", content_url)

        # Проверка признаков авторизации
        body = await page.content()
        authed = ("notebooks" in body.lower()) or ("runtime" in content_url.lower())
        signin_present = "Войдите" in body or "Sign in" in body or "accounts.google" in content_url
        print("Признак авторизации (notebooks/runtime):", authed)
        print("Признак окна входа:", signin_present)

        result = {
            "title": title,
            "url": content_url,
            "authenticated": authed and not signin_present,
        }
        print("\nPROBE RESULT:", json.dumps(result, ensure_ascii=False))
        await page.close()
        return result


if __name__ == "__main__":
    asyncio.run(probe())
