#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright
CDP="http://localhost:9222"
async def main():
    p=await async_playwright().start()
    b=await p.chromium.connect_over_cdp(CDP)
    ctx=b.contexts[0]
    page=None
    for pg in ctx.pages:
        try:
            if "Quant_ML_Training" in pg.url: page=pg; break
        except: pass
    if not page: print("NO_TAB"); await p.stop(); return
    await page.bring_to_front()
    await asyncio.sleep(2)
    # перезагрузка страницы (runtime сохраняется)
    print("reloading")
    await page.reload(wait_until="domcontentloaded")
    await asyncio.sleep(15)
    print("reloaded")
    await page.screenshot(path="/tmp/after_reload.png")
    await p.stop()
asyncio.run(main())
