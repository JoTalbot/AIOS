#!/usr/bin/env python3
import sys, asyncio
from playwright.async_api import async_playwright
async def main():
    nb_key = sys.argv[1] if len(sys.argv)>1 else "AIOS_Colab_Quant_ML_Training"
    p=await async_playwright().start()
    b=await p.chromium.connect_over_cdp("http://localhost:9222")
    ctx=b.contexts[0]
    # ищем popup / новую вкладку с oauth
    for pg in ctx.pages:
        url=pg.url
        if "oauth" in url or "accounts.google.com" in url:
            try:
                t=await pg.title()
                body=await pg.evaluate("() => document.body.innerText")
                print(f"=== POPUP [{t}] {url[:60]}")
                print(body[:300].replace(chr(10),' | '))
            except Exception: pass
    # вывод главной вкладки на предмет mount
    for pg in ctx.pages:
        if nb_key in pg.url:
            body=await pg.evaluate("() => document.body.innerText")
            print("\n=== MAIN tail (ищем DRIVE) ===")
            for kw in ["Mounted","Монту","DRIVE_COPY","drive","Мій диск","My Drive","Go to this URL","Відкрити цю адресу"]:
                if kw.lower() in body.lower():
                    i=body.lower().find(kw.lower())
                    print(f"  [{kw}] ...{body[max(0,i-60):i+120]!r}")
            break
    await p.stop()
asyncio.run(main())
