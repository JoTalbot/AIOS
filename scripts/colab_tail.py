#!/usr/bin/env python3
import sys, asyncio
from playwright.async_api import async_playwright
async def main():
    nb_key = sys.argv[1] if len(sys.argv)>1 else "AIOS_Colab_Quant_ML_Training"
    p=await async_playwright().start()
    b=await p.chromium.connect_over_cdp("http://localhost:9222")
    ctx=b.contexts[0]
    for pg in ctx.pages:
        if nb_key in pg.url:
            body=await pg.evaluate("() => document.body.innerText")
            print("=== ХВОСТ (последние 2500) ===")
            print(body[-2500:])
            break
    await p.stop()
asyncio.run(main())
