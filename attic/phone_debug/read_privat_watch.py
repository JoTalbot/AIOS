#!/usr/bin/env python3
"""Ждёт появления вкладки кабинета Приват24 (/wallet) и читает баланс."""
import asyncio
import re
import sys
import time


async def main():
    from aios_core.platforms.privat_chrome_twin_adapter import PrivatChromeTwinAdapter
    a = PrivatChromeTwinAdapter()
    from playwright.async_api import async_playwright
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp(a.cdp_url)
    ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
    print("[watch] жду вкладку кабинета Приват24 (/wallet) до 180с...", flush=True)
    deadline = time.time() + 180
    while time.time() < deadline:
        for pg in ctx.pages:
            u = pg.url or ""
            if "/wallet" in u:
                print("[watch] нашли кабинет:", u, flush=True)
                await pg.bring_to_front()
                await pg.wait_for_timeout(3000)
                body = (await pg.inner_text("body"))
                print("URL:", pg.url, flush=True)
                for l in body.splitlines():
                    l = l.strip()
                    if any(k in l for k in ("Універсальна", "Гривня", "UAH", "грн", "••••", "Баланс", "Доступно")):
                        print(f"  {l[:90]}", flush=True)
                amounts = re.findall(r"([\d\s\u00a0]+[.,]\d{2})\s*(?:грн|₴|uah)", body)
                print("СУММЫ:", [x.replace("\u00a0"," ").replace(" ","") for x in amounts][:12], flush=True)
                print("BALANCE:", a._extract_balance(body), flush=True)
                return 0
        await asyncio.sleep(4)
    print("[watch] кабинет не появился за 180с", flush=True)
    return 1


loop = asyncio.new_event_loop()
try:
    rc = loop.run_until_complete(main())
    sys.stdout.flush()
    sys.exit(rc)
except Exception as e:
    print("ERR:", str(e)[:120])
    sys.stdout.flush()
    sys.exit(1)
finally:
    try:
        loop.run_until_complete(loop.shutdown_asyncgens())
    except Exception:
        pass
    loop.close()
