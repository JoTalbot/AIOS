#!/usr/bin/env python3
import sys, asyncio
from playwright.async_api import async_playwright

async def main():
    nb_key = sys.argv[1] if len(sys.argv) > 1 else "AIOS_Colab_Quant_ML_Training"
    out = sys.argv[2] if len(sys.argv) > 2 else "/root/AIOS/data/colab_screenshot.png"
    p = await async_playwright().start()
    b = await p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = b.contexts[0]
    page = None
    for pg in ctx.pages:
        if nb_key in pg.url: page = pg; break
    if not page:
        print("вкладка не найдена"); await p.stop(); return
    await page.set_viewport_size({"width": 1600, "height": 1000})
    await page.screenshot(path=out, full_page=False)
    print("saved", out)
    await p.stop()

asyncio.run(main())
