#!/usr/bin/env python3
"""Обработать OAuth Drive: выбрать аккаунт и разрешить доступ."""
import sys, asyncio
from playwright.async_api import async_playwright

async def main():
    p=await async_playwright().start()
    b=await p.chromium.connect_over_cdp("http://localhost:9222")
    ctx=b.contexts[0]
    page=None
    for pg in ctx.pages:
        if "accounts.google.com/signin/oauth" in pg.url:
            page=pg; break
    if not page:
        print("oauth вкладка не найдена")
        # покажем все вкладки
        for pg in ctx.pages:
            print(" -", pg.url[:70])
        await p.stop(); return
    await page.bring_to_front()
    await page.set_viewport_size({"width":800,"height":700})
    await asyncio.sleep(2)
    body=await page.evaluate("() => document.body.innerText")
    print("=== OAuth содержимое ===")
    print(body[:800])
    await page.screenshot(path="/root/AIOS/data/oauth.png")
    print("скриншот сохранён")
    await p.stop()

asyncio.run(main())
