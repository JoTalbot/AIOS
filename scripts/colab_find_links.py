#!/usr/bin/env python3
import sys, asyncio, re
from playwright.async_api import async_playwright
async def main():
    nb_key=sys.argv[1] if len(sys.argv)>1 else "AIOS_Colab_Quant_ML_Training"
    p=await async_playwright().start()
    b=await p.chromium.connect_over_cdp("http://localhost:9222")
    ctx=b.contexts[0]
    for pg in ctx.pages:
        if nb_key in pg.url:
            body=await pg.evaluate("() => document.body.innerText")
            # ссылки
            links=re.findall(r'https://transfer\.sh/[^\s\"\\\\]+|https://file\.io/[^\s\"\\\\]+', body)
            print("Ссылки:", links[:6])
            for kw in ["FILE_COUNT","TRANSFER_LINK","FILEIO_LINK","DONE","transfer_sh_fail","fileio_fail","Error","Exception"]:
                if kw in body:
                    i=body.find(kw)
                    print(f"[{kw}] ...{body[max(0,i-30):i+150]!r}")
            # если нет - хвост
            if not links:
                print("=== ХВОСТ ===")
                print(body[-400:])
            break
    await p.stop()
asyncio.run(main())
