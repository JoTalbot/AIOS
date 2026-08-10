#!/usr/bin/env python3
import sys, asyncio
from playwright.async_api import async_playwright
async def main():
    p=await async_playwright().start()
    b=await p.chromium.connect_over_cdp("http://localhost:9222")
    ctx=b.contexts[0]
    page=None
    for pg in ctx.pages:
        if "signin/oauth" in pg.url:
            page=pg; break
    if not page:
        print("oauth не найдена"); await p.stop(); return
    await page.bring_to_front()
    await page.set_viewport_size({"width":800,"height":700})
    await asyncio.sleep(2)
    body=await page.evaluate("() => document.body.innerText")
    print("=== BODY ===")
    print(body[:1000])
    await page.screenshot(path="/root/AIOS/data/oauth2.png")
    print("shot saved")
    await p.stop()
asyncio.run(main())
