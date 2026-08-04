#!/usr/bin/env python3
"""Автовход в àБізнес с пошаговой диагностикой (лог всех шагов и видимых полей)."""
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, "/root/AIOS")
SECRETS = Path("/root/AIOS/data/.bank_secrets.json")


async def visible_els(page, selectors, label):
    out = []
    for sel in selectors:
        try:
            loc = page.locator(sel)
            n = await loc.count()
            vis = 0
            for i in range(min(n, 5)):
                try:
                    if await loc.nth(i).is_visible():
                        vis += 1
                except Exception:
                    pass
            if n:
                out.append(f"{label}[{sel}]: n={n} vis={vis}")
        except Exception:
            pass
    return "; ".join(out)


async def main():
    from aios_core.platforms.abank_business_chrome_twin_adapter import ABankBusinessChromeTwinAdapter
    sec = json.loads(SECRETS.read_text(encoding="utf-8")).get("abank_biz", {})
    phone = sec.get("phone", "380959052288")
    password = sec.get("password", "")

    a = ABankBusinessChromeTwinAdapter()
    from playwright.async_api import async_playwright
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp(a.cdp_url)
    ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
    page = await ctx.new_page()
    print("[1] открываю", a.login_url, flush=True)
    await page.goto(a.login_url, wait_until="domcontentloaded", timeout=45000)
    await page.wait_for_timeout(6000)
    print("[2] URL:", page.url, flush=True)
    print("[3] body:", (await page.inner_text("body"))[:250].replace("\n", " | "), flush=True)
    print("[4] видимые:", await visible_els(page, [
        "input[type='tel']", "input[type='text']", "input[type='password']",
        "input:not([type])", "button", "input[name*='phone']", "input[name*='pass']",
    ], "EL"), flush=True)

    # ввести телефон
    filled = False
    for sel in ["input[type='tel']", "input[type='text']", "input:not([type])"]:
        try:
            box = page.locator(sel).first
            if await box.count() and await box.is_visible():
                await box.click(timeout=3000)
                await box.fill(phone)
                filled = True
                print("[5] телефон введён в", sel, flush=True)
                break
        except Exception as e:
            print("[5] err", sel, str(e)[:60], flush=True)
    print("[5] phone_filled:", filled, flush=True)

    # нажать кнопку продолжения
    clicked = False
    for sel in ["button:has-text('Продовжити')", "button:has-text('Далі')", "button:has-text('Увійти')", "button[type='submit']"]:
        try:
            b = page.locator(sel).first
            if await b.count():
                await b.click(timeout=2500)
                clicked = True
                print("[6] нажал", sel, flush=True)
                break
        except Exception:
            continue
    print("[6] submit_clicked:", clicked, flush=True)
    await page.wait_for_timeout(4000)
    print("[7] после submit URL:", page.url, flush=True)
    print("[7] body:", (await page.inner_text("body"))[:250].replace("\n", " | "), flush=True)
    print("[8] видимые:", await visible_els(page, [
        "input[type='password']", "input[type='tel']", "input[type='text']",
        "input[name*='pass']", "input[name*='password']", "button",
    ], "EL"), flush=True)

    # ввести пароль
    if password:
        pfilled = False
        for sel in ["input[type='password']", "input[name*='pass']", "input[name*='password']"]:
            try:
                box = page.locator(sel).first
                if await box.count() and await box.is_visible():
                    await box.click(timeout=3000)
                    await box.fill(password)
                    pfilled = True
                    print("[9] пароль введён в", sel, flush=True)
                    break
            except Exception as e:
                print("[9] err", sel, str(e)[:60], flush=True)
        print("[9] pass_filled:", pfilled, flush=True)
        for sel in ["button:has-text('Увійти')", "button:has-text('Продовжити')", "button:has-text('Далі')", "button[type='submit']"]:
            try:
                b = page.locator(sel).first
                if await b.count():
                    await b.click(timeout=2500)
                    print("[10] нажал", sel, flush=True)
                    break
            except Exception:
                continue
        await page.wait_for_timeout(4000)
        print("[11] после пароля URL:", page.url, flush=True)
        print("[11] body:", (await page.inner_text("body"))[:250].replace("\n", " | "), flush=True)

    print("[12] DONE", flush=True)
    # не закрываем, чтобы вкладка осталась
    await asyncio.sleep(5)


loop = asyncio.new_event_loop()
try:
    loop.run_until_complete(main())
    sys.stdout.flush()
except Exception as e:
    print("ERR:", str(e)[:200])
    sys.stdout.flush()
finally:
    try:
        loop.run_until_complete(loop.shutdown_asyncgens())
    except Exception:
        pass
    loop.close()
