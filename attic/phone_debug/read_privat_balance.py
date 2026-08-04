#!/usr/bin/env python3
"""Читает баланс Приват24 из существующей вкладки кабинета (без новой вкладки)."""
import asyncio
import sys


async def main():
    from aios_core.platforms.privat_chrome_twin_adapter import PrivatChromeTwinAdapter
    a = PrivatChromeTwinAdapter()
    from playwright.async_api import async_playwright
    pw = await async_playwright().start()
    browser = await pw.chromium.connect_over_cdp(a.cdp_url)
    ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
    # найти вкладку кабинета (wallet/cards)
    target = None
    for pg in ctx.pages:
        u = pg.url or ""
        if "/wallet" in u or "privat24" in u:
            target = pg
            break
    if not target:
        print("НЕТ вкладки Приват24 в Chrome", flush=True)
        return 1
    await target.bring_to_front()
    await target.wait_for_timeout(3000)
    print("URL:", target.url, flush=True)
    body = (await target.inner_text("body"))
    # поиск балансов: карточки с суммами
    lines = [l.strip() for l in body.splitlines() if l.strip()]
    # показать строки с картой/балансом
    for i, l in enumerate(lines):
        if any(k in l for k in ("Універсальна", "Гривня", "UAH", "грн", "••••", "Баланс", "Доступно")):
            print(f"  {l[:80]}", flush=True)
    # ищем все суммы в гривнах
    import re
    amounts = re.findall(r"([\d\s\u00a0]+[.,]\d{2})\s*(?:грн|₴|uah)", body)
    print("BALANCE match:", a._extract_balance(body), flush=True)
    print("Суммы (грн):", [x.replace("\u00a0"," ").replace(" ","") for x in amounts][:10], flush=True)
    return 0


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
