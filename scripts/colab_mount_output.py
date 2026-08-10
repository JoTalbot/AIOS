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
            # ищем URL в выводе
            urls=re.findall(r"https://accounts\.google\.com[^\s\"\\\\']+", body)
            print("URL авторизации:", urls[:3])
            # ищем текст запроса кода
            for kw in ["Enter your authorization code","Введіть код","введіть код авторизації","authorization code","код авторизації","Монтування","Mounted","mount"]:
                if kw.lower() in body.lower():
                    i=body.lower().find(kw.lower())
                    print(f"[{kw}] ...{body[max(0,i-30):i+150]!r}")
            # хвост вывода
            print("=== ХВОСТ ===")
            print(body[-600:])
            break
    await p.stop()
asyncio.run(main())
