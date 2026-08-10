#!/usr/bin/env python3
import sys, asyncio
from playwright.async_api import async_playwright

async def main():
    nb_key = sys.argv[1] if len(sys.argv) > 1 else "AIOS_Colab_Quant_ML_Training"
    p = await async_playwright().start()
    b = await p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = b.contexts[0]
    pages = [pg for pg in ctx.pages]
    print("=== Всего вкладок:", len(pages))
    for pg in pages:
        url = pg.url
        if "outputframe" in url or nb_key in url:
            try:
                body = await pg.main_frame.evaluate("() => document.body ? document.body.innerText : ''")
                print(f"\n--- [{url[:60]}] ---")
                print(body[:1200])
            except Exception as e:
                print(f"--- err {url[:40]}: {e}")
    await p.stop()

asyncio.run(main())
