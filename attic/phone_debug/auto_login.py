#!/usr/bin/env python3
"""Полный автовход в банк: телефон + пароль + SMS-код, всё сам.

Пароль/телефон берутся из data/.bank_secrets.json (права 600, не в git).
"""
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, "/root/AIOS")

SECRETS_PATH = Path("/root/AIOS/data/.bank_secrets.json")


def _secrets(bank):
    try:
        d = json.loads(SECRETS_PATH.read_text(encoding="utf-8"))
        return d.get(bank, {})
    except Exception:
        return {}


async def fill_code(a, target, code):
    filled = False
    for sel in [a.code_field_selector]:
        try:
            box = target.locator(sel).first
            if await box.count() and await box.is_visible():
                await box.click(timeout=2000)
                await box.fill(code)
                await box.press("Enter")
                filled = True
                break
        except Exception:
            continue
    if not filled:
        digits = [c for c in code if c.isdigit()]
        inputs = target.locator("input[type='tel'], input[type='text'], input:not([type])")
        n = await inputs.count()
        done = 0
        for i in range(n):
            try:
                box = inputs.nth(i)
                if not await box.is_visible():
                    continue
                if done < len(digits):
                    await box.click(timeout=800)
                    await box.fill(digits[done])
                    done += 1
            except Exception:
                break
        filled = done >= 3
    return filled


async def main(bank):
    if bank == "abank_biz":
        from aios_core.platforms.abank_business_chrome_twin_adapter import ABankBusinessChromeTwinAdapter as C
    elif bank == "privat":
        from aios_core.platforms.privat_chrome_twin_adapter import PrivatChromeTwinAdapter as C
    else:
        from aios_core.platforms.privat_business_chrome_twin_adapter import PrivatBusinessChromeTwinAdapter as C

    sec = _secrets(bank)
    phone = sec.get("phone", "380959052288")
    password = sec.get("password", "")

    a = C()
    print(f"[{bank}] открываю {a.login_url}", flush=True)
    # Открываем НОВУЮ вкладку напрямую через CDP (устойчиво к чужим вкладкам)
    from playwright.async_api import async_playwright
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp(a.cdp_url)
    ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
    page = await ctx.new_page()
    await page.goto(a.login_url, wait_until="domcontentloaded", timeout=45000)
    await page.wait_for_timeout(5000)

    # уже залогинен?
    try:
        if await a.is_logged_in(page):
            print(f"[{bank}] ✅ уже авторизован", flush=True)
            return 0
    except Exception:
        pass

    # ввести телефон
    filled_login = False
    for sel in [a.login_field_selector]:
        try:
            box = page.locator(sel).first
            if await box.count() and await box.is_visible():
                await box.click(timeout=4000)
                await box.fill(phone)
                filled_login = True
                break
        except Exception:
            continue
    print(f"[{bank}] телефон введён: {filled_login}", flush=True)
    await a._click_submit(page)
    await page.wait_for_timeout(3500)

    # ввести пароль (для abank_biz)
    if a.needs_password and password:
        pfilled = False
        for sel in [a.password_field_selector]:
            try:
                box = page.locator(sel).first
                if await box.count() and await box.is_visible():
                    await box.click(timeout=3000)
                    await box.fill(password)
                    pfilled = True
                    break
            except Exception:
                continue
        print(f"[{bank}] пароль введён: {pfilled}", flush=True)
        await a._click_submit(page)
        await page.wait_for_timeout(3000)

    # ждём SMS и вводим (до 150с)
    print(f"[{bank}] жду SMS-код (до 150с)...", flush=True)
    deadline = time.time() + 150
    seen = set()
    while time.time() < deadline:
        await page.wait_for_timeout(3000)
        try:
            if await a.is_logged_in(page):
                print(f"[{bank}] ✅ вход прошёл (кабинет)", flush=True)
                return 0
        except Exception:
            pass
        code = await a._read_sms_code()
        if code and code not in seen:
            seen.add(code)
            print(f"[{bank}] 📩 SMS: {code}", flush=True)
            ok = await fill_code(a, page, code)
            print(f"[{bank}] код введён: {ok}", flush=True)
            await page.wait_for_timeout(8000)
            try:
                if await a.is_logged_in(page):
                    print(f"[{bank}] ✅ вход подтверждён", flush=True)
                    return 0
            except Exception:
                pass
    # финал
    try:
        if await a.is_logged_in(page):
            print(f"[{bank}] ✅ вход прошёл", flush=True)
            return 0
    except Exception:
        pass
    print(f"[{bank}] не получил SMS за 150с", flush=True)
    return 1


if __name__ == "__main__":
    bank = sys.argv[1] if len(sys.argv) > 1 else "abank_biz"
    loop = asyncio.new_event_loop()
    try:
        rc = loop.run_until_complete(main(bank))
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
