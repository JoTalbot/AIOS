#!/usr/bin/env python3
"""Автовход àБізнес: вводит телефон, доходит до подтверждения в приложении,
ждёт пока ты подтвердишь push в àbank24, затем проверяет вход."""
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, "/root/AIOS")
SECRETS = Path("/root/AIOS/data/.bank_secrets.json")


async def main():
    from aios_core.platforms.abank_business_chrome_twin_adapter import ABankBusinessChromeTwinAdapter
    sec = json.loads(SECRETS.read_text(encoding="utf-8")).get("abank_biz", {})
    phone = sec.get("phone", "+380959052288")

    a = ABankBusinessChromeTwinAdapter()
    from playwright.async_api import async_playwright
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp(a.cdp_url)
    ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
    page = await ctx.new_page()
    print("[1] открываю", a.login_url, flush=True)
    await page.goto(a.login_url, wait_until="domcontentloaded", timeout=45000)
    await page.wait_for_timeout(6000)

    # ввести телефон
    for sel in ["input[type='text']", "input[type='tel']", "input:not([type])"]:
        try:
            box = page.locator(sel).first
            if await box.count() and await box.is_visible():
                await box.click(timeout=3000)
                await box.fill(phone)
                print("[2] телефон введён", flush=True)
                break
        except Exception:
            continue
    for sel in ["button:has-text('Продовжити')", "button:has-text('Далі')", "button[type='submit']"]:
        try:
            b = page.locator(sel).first
            if await b.count():
                await b.click(timeout=2500)
                print("[3] нажал Продовжити", flush=True)
                break
        except Exception:
            continue
    await page.wait_for_timeout(4000)
    print("[4] URL:", page.url, flush=True)
    print("[4] body:", (await page.inner_text("body"))[:300].replace("\n", " | "), flush=True)

    # ждём подтверждения в приложении (до 180с)
    print("[5] ⏳ Подтвердите вход в приложении àbank24 на телефоне (до 180с)...", flush=True)
    deadline = time.time() + 180
    while time.time() < deadline:
        await page.wait_for_timeout(5000)
        try:
            # проверяем, что страница сменилась с /auth/app на кабинет
            url = page.url or ""
            body = (await page.inner_text("body"))[:300]
            if "/app" not in url and "Вхід у систему" not in body and "підтвердіть запит" not in body:
                print("[6] ✅ Страница изменилась, проверяю...", flush=True)
                print("    URL:", url, flush=True)
                print("    body:", body.replace("\n", " | ")[:250], flush=True)
                print("    is_logged_in:", await a.is_logged_in(page), flush=True)
                return 0
        except Exception as e:
            print("[6] err", str(e)[:80], flush=True)
    print("[6] время вышло (180с)", flush=True)
    return 1


loop = asyncio.new_event_loop()
try:
    rc = loop.run_until_complete(main())
    sys.stdout.flush()
    sys.exit(rc)
except Exception as e:
    print("ERR:", str(e)[:150])
    sys.stdout.flush()
    sys.exit(1)
finally:
    try:
        loop.run_until_complete(loop.shutdown_asyncgens())
    except Exception:
        pass
    loop.close()
