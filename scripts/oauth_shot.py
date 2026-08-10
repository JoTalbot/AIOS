#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright
async def main():
    p=await async_playwright().start()
    b=await p.chromium.connect_over_cdp("http://localhost:9222")
    ctx=b.contexts[0]
    found=False
    for pg in ctx.pages:
        if "signin/oauth" in pg.url:
            await pg.bring_to_front()
            await pg.set_viewport_size({"width":900,"height":800})
            await asyncio.sleep(3)
            await pg.screenshot(path="/root/AIOS/data/oauth_shot.png")
            found=True
            print("shot saved")
            break
    if not found: print("oauth не найдена")
    await p.stop()
asyncio.run(main())
