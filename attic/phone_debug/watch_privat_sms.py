#!/usr/bin/env python3
"""Мониторит SMS для Приват24 и вводит код в открытую вкладку Приват24."""
import asyncio
import sys
import time

sys.path.insert(0, "/root/AIOS")


async def main():
    from aios_core.platforms.privat_chrome_twin_adapter import PrivatChromeTwinAdapter
    a = PrivatChromeTwinAdapter()
    from playwright.async_api import async_playwright
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp(a.cdp_url)
    ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
    # найти вкладку Приват24
    target = None
    for pg in ctx.pages:
        if "privat24" in (pg.url or ""):
            target = pg
            break
    if not target:
        print("[watch] не найдена вкладка Приват24", flush=True)
        return 1
    try:
        await target.bring_to_front()
    except Exception:
        pass
    print(f"[watch] вкладка Приват24: {target.url}", flush=True)
    deadline = time.time() + 240
    seen = set()
    while time.time() < deadline:
        await asyncio.sleep(4)
        # код ввёден? проверяем что появился кабинет
        try:
            if await a.is_logged_in(target):
                print("[watch] ✅ вход прошёл (кабинет)", flush=True)
                return 0
        except Exception:
            pass
        code = await a._read_sms_code()
        if code and code not in seen:
            seen.add(code)
            print(f"[watch] 📩 SMS: {code}", flush=True)
            filled = False
            # ввести в поля модалки Приват24 (по цифрам)
            digits = [c for c in code if c.isdigit()]
            inputs = target.locator("input")
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
            print(f"[watch] код введён: {filled}", flush=True)
            await asyncio.sleep(8)
    try:
        if await a.is_logged_in(target):
            print("[watch] ✅ вход прошёл", flush=True)
            return 0
    except Exception:
        pass
    print("[watch] SMS не получен за 240с", flush=True)
    return 1


loop = asyncio.new_event_loop()
try:
    rc = loop.run_until_complete(main())
    sys.stdout.flush()
    sys.exit(rc)
except Exception as e:
    print("[watch] ERR:", str(e)[:120])
    sys.stdout.flush()
    sys.exit(1)
finally:
    try:
        loop.run_until_complete(loop.shutdown_asyncgens())
    except Exception:
        pass
    loop.close()
