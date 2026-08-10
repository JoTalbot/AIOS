#!/usr/bin/env python3
import sys, asyncio, re
from playwright.async_api import async_playwright
async def main():
    nb_key=sys.argv[1] if len(sys.argv)>1 else "AIOS_Colab_Quant_ML_Training"
    p=await async_playwright().start()
    b=await p.chromium.connect_over_cdp("http://localhost:9222")
    ctx=b.contexts[0]
    print("=== вкладки ===")
    for pg in ctx.pages:
        u=pg.url
        if "colab.googleusercontent" in u or "outputframe" in u or "output" in u.lower():
            try:
                body=await pg.main_frame.evaluate("() => document.body ? document.body.innerText : ''")
                body=body or ""
                # ищем ссылки/маркеры
                if any(k in body for k in ["TRANSFER","FILEIO","transfer.sh","file.io","FILE_COUNT","DONE","https://"]):
                    print(f"--- [{u[:50]}] ---")
                    print(body[:1000])
            except Exception:
                pass
    await p.stop()
asyncio.run(main())
