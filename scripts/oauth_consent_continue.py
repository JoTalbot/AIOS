#!/usr/bin/env python3
"""Нажать Продолжить в consent и дождаться завершения."""
import sys, asyncio
from playwright.async_api import async_playwright
CDP="http://localhost:9222"
async def main():
    p=await async_playwright().start()
    b=await p.chromium.connect_over_cdp(CDP)
    ctx=b.contexts[0]
    page=None
    for pg in ctx.pages:
        if "consentsummary" in pg.url: page=pg; break
    if not page: print("consent не найдена"); await p.stop(); return
    await page.bring_to_front()
    await asyncio.sleep(2)
    for txt in ["Продолжить","Continue","Разрешить","Дозволити"]:
        try:
            loc=page.get_by_role("button", name=txt)
            if await loc.count()>0:
                await loc.first.click(timeout=3000)
                print("Клик:", txt); break
        except Exception:
            continue
    await asyncio.sleep(15)
    # oauth закрылась?
    closed=True
    for pg in ctx.pages:
        if "consentsummary" in pg.url or "signin/oauth" in pg.url: closed=False
    print("OAuth вкладка закрылась:", closed)
    await p.stop()
asyncio.run(main())
