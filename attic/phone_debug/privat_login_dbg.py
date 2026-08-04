#!/usr/bin/env python3
"""Автовход в Приват24: телефон 959052288 + SMS. Диагностика шагов."""
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, "/root/AIOS")
PHONE = "959052288"


async def vis(page, sels):
    out = []
    for s in sels:
        try:
            l = page.locator(s)
            n = await l.count()
            if n:
                out.append(f"{s}:n{n}")
        except Exception:
            pass
    return "; ".join(out)


async def main():
    from aios_core.platforms.privat_chrome_twin_adapter import PrivatChromeTwinAdapter
    a = PrivatChromeTwinAdapter()
    from playwright.async_api import async_playwright
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp(a.cdp_url)
    ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
    page = await ctx.new_page()
    print("[1] открываю", a.login_url, flush=True)
    await page.goto(a.login_url, wait_until="domcontentloaded", timeout=45000)
    await page.wait_for_timeout(8000)
    print("[2] URL:", page.url, flush=True)
    print("[3] body:", (await page.inner_text("body"))[:300].replace("\n", " | "), flush=True)
    print("[4] inputs:", await vis(page, ["input[type='tel']", "input[type='text']", "input:not([type])", "button"]), flush=True)

    # ввести телефон в первое tel-поле
    filled = False
    for sel in ["input[type='tel']", "input:not([type])", "input[type='text']"]:
        try:
            box = page.locator(sel).first
            if await box.count() and await box.is_visible():
                await box.click(timeout=3000)
                await box.fill(PHONE)
                filled = True
                print("[5] телефон введён в", sel, flush=True)
                break
        except Exception as e:
            print("[5] err", sel, str(e)[:60], flush=True)
    print("[5] filled:", filled, flush=True)

    # нажать Вхід/Далі
    clicked = False
    for sel in ["button:has-text('Вхід')", "button:has-text('Далі')", "button:has-text('Продовжити')", "button[type='submit']"]:
        try:
            b = page.locator(sel).first
            if await b.count():
                await b.click(timeout=2500)
                clicked = True
                print("[6] нажал", sel, flush=True)
                break
        except Exception:
            continue
    print("[6] clicked:", clicked, flush=True)
    await page.wait_for_timeout(4000)
    print("[7] после submit URL:", page.url, flush=True)
    print("[7] body:", (await page.inner_text("body"))[:300].replace("\n", " | "), flush=True)
    print("[8] inputs:", await vis(page, ["input[type='tel']", "input[type='text']", "input:not([type])", "input[name*='code']", "input[placeholder*='код']", "button"]), flush=True)
    print("[9] DONE", flush=True)
    await asyncio.sleep(3)


loop = asyncio.new_event_loop()
try:
    loop.run_until_complete(main())
    sys.stdout.flush()
except Exception as e:
    print("ERR:", str(e)[:150])
    sys.stdout.flush()
finally:
    try:
        loop.run_until_complete(loop.shutdown_asyncgens())
    except Exception:
        pass
    loop.close()
