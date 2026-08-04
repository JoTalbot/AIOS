#!/usr/bin/env python3
"""Надёжный автовход Приват24: новый контекст, телефон 959052288, SMS."""
import asyncio
import sys
import time

sys.path.insert(0, "/root/AIOS")
PHONE = "959052288"


async def fill_sms(a, page, code):
    filled = False
    for sel in [a.code_field_selector]:
        try:
            box = page.locator(sel).first
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
        inputs = page.locator("input[type='tel'], input[type='text'], input:not([type])")
        n = await inputs.count()
        done = 0
        for i in range(n):
            try:
                box = inputs.nth(i)
                if not await box.is_visible():
                    continue
                if done < len(digits):
                    await box.click(timeout=600)
                    await box.fill(digits[done])
                    done += 1
            except Exception:
                break
        filled = done >= 3
    return filled


async def main():
    from aios_core.platforms.privat_chrome_twin_adapter import PrivatChromeTwinAdapter
    a = PrivatChromeTwinAdapter()
    from playwright.async_api import async_playwright
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp(a.cdp_url)
    ctx = await browser.new_context()  # НОВЫЙ контекст
    page = await ctx.new_page()
    await page.goto("https://next.privat24.ua/", wait_until="domcontentloaded", timeout=45000)
    await page.wait_for_timeout(8000)
    print("[1] URL:", page.url, flush=True)

    # открыть модалку входа
    clicked = False
    for sel in ["button:has-text('Вхід')", "[data-testid*='login']", "a:has-text('Вхід')"]:
        try:
            el = page.locator(sel).first
            if await el.count():
                await el.click(timeout=2500)
                clicked = True
                break
        except Exception:
            continue
    await page.wait_for_timeout(2500)
    print("[2] модалка входа открыта:", clicked, flush=True)

    # ввести телефон в поле карты модалки
    entered = False
    for sel in ["input[placeholder*='0000']", "input[placeholder*='0 0']", "input[type='tel']"]:
        try:
            l = page.locator(sel)
            n = await l.count()
            for i in range(min(n, 8)):
                try:
                    box = l.nth(i)
                    if await box.is_visible():
                        await box.click(timeout=2000)
                        await box.press("Control+a")
                        await box.fill(PHONE)
                        await page.wait_for_timeout(400)
                        val = await box.input_value()
                        print(f"[3] ввёл в {sel}[{i}]: '{val}'", flush=True)
                        entered = True
                        break
                except Exception as e:
                    continue
            if entered:
                break
        except Exception:
            continue
    print("[3] entered:", entered, flush=True)

    # нажать Далі/Вхід
    for sel in ["button:has-text('Далі')", "button:has-text('Вхід')", "button[type='submit']"]:
        try:
            b = page.locator(sel).first
            if await b.count() and await b.is_visible():
                await b.click(timeout=2500)
                print("[4] нажал", sel, flush=True)
                break
        except Exception:
            continue
    await page.wait_for_timeout(4000)
    print("[5] URL:", page.url, flush=True)
    print("[5] body:", (await page.inner_text("body"))[:250].replace("\n", " | "), flush=True)

    # ждём SMS до 150с
    print("[6] жду SMS (до 150с)...", flush=True)
    deadline = time.time() + 150
    seen = set()
    while time.time() < deadline:
        await page.wait_for_timeout(3000)
        try:
            if await a.is_logged_in(page):
                print("[6] ✅ вход прошёл", flush=True)
                return 0
        except Exception:
            pass
        code = await a._read_sms_code()
        if code and code not in seen:
            seen.add(code)
            print(f"[7] 📩 SMS: {code}", flush=True)
            ok = await fill_sms(a, page, code)
            print(f"[7] код введён: {ok}", flush=True)
            await page.wait_for_timeout(8000)
            try:
                if await a.is_logged_in(page):
                    print("[7] ✅ вход подтверждён", flush=True)
                    return 0
            except Exception:
                pass
    try:
        if await a.is_logged_in(page):
            print("[8] ✅ вход прошёл", flush=True)
            return 0
    except Exception:
        pass
    print("[8] SMS не получен за 150с", flush=True)
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
