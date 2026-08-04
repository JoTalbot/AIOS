#!/usr/bin/env python3
"""Автовход Приват24: клик Вхід -> модалка -> телефон -> SMS."""
import asyncio
import sys
import time

sys.path.insert(0, "/root/AIOS")
PHONE = "959052288"


async def main():
    from aios_core.platforms.privat_chrome_twin_adapter import PrivatChromeTwinAdapter
    a = PrivatChromeTwinAdapter()
    from playwright.async_api import async_playwright
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp(a.cdp_url)
    ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
    page = await ctx.new_page()
    await page.goto(a.login_url, wait_until="domcontentloaded", timeout=45000)
    await page.wait_for_timeout(8000)
    print("[1] URL:", page.url, flush=True)

    # кликнуть Вхід чтобы открыть модалку
    clicked = False
    for sel in ["button:has-text('Вхід')", "a:has-text('Вхід')", "[data-testid*='login']"]:
        try:
            el = page.locator(sel).first
            if await el.count():
                await el.click(timeout=2500)
                clicked = True
                print("[2] клик Вхід:", sel, flush=True)
                break
        except Exception:
            continue
    await page.wait_for_timeout(3000)
    print("[2] clicked:", clicked, flush=True)
    print("[3] body:", (await page.inner_text("body"))[:300].replace("\n", " | "), flush=True)

    # найти видимые поля в модалке
    for sel in ["input[type='tel']", "input[placeholder*='0000']", "input:not([type])", "input[type='text']"]:
        try:
            l = page.locator(sel)
            n = await l.count()
            for i in range(min(n, 5)):
                try:
                    if await l.nth(i).is_visible():
                        print(f"[4] видимое поле {sel}[{i}]", flush=True)
                except Exception:
                    pass
        except Exception:
            pass

    # ввести телефон/карту именно в поле карты модалки входа (placeholder 0000)
    entered = False
    for sel in ["input[placeholder*='0000']", "input[placeholder*='0 0']", "input[type='tel']"]:
        try:
            l = page.locator(sel)
            n = await l.count()
            for i in range(min(n, 8)):
                try:
                    box = l.nth(i)
                    if await box.is_visible():
                        # кликнуть и ввести
                        await box.click(timeout=2000)
                        await box.press("Control+a")
                        await box.fill(PHONE)
                        await page.wait_for_timeout(500)
                        val = await box.input_value()
                        print(f"[5] ввёл в {sel}[{i}], значение: '{val}'", flush=True)
                        entered = True
                        break
                except Exception as e:
                    print(f"[5] err {sel}[{i}]: {str(e)[:50]}", flush=True)
                    continue
            if entered:
                break
        except Exception:
            continue
    print("[5] entered:", entered, flush=True)

    # нажать кнопку входа в модалке
    for sel in ["button:has-text('Далі')", "button:has-text('Вхід')", "button:has-text('Продовжити')", "button[type='submit']"]:
        try:
            b = page.locator(sel).first
            if await b.count() and await b.is_visible():
                await b.click(timeout=2500)
                print("[6] нажал", sel, flush=True)
                break
        except Exception:
            continue
    await page.wait_for_timeout(4000)
    print("[7] body после:", (await page.inner_text("body"))[:300].replace("\n", " | "), flush=True)
    print("[8] DONE", flush=True)
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
