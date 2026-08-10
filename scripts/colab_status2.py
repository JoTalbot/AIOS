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
            print("URL:", pg.url[:90])
            try:
                body=await pg.evaluate("() => document.body.innerText")
                print("len:", len(body))
                for kw in ["binance/","bybit/","okx/","kraken/","skip","Данные:","Дані:","Зависимости","XGBoost","CatBoost","Лучшая","Устройство","Загружено в R2","Модели сохранены","epoch","Epoch"]:
                    if kw.lower() in body.lower():
                        i=body.lower().find(kw.lower())
                        print(f"  [{kw}] ...{body[max(0,i-30):i+60]!r}")
            except Exception as e:
                print("eval err", e)
            break
    await p.stop()
asyncio.run(main())
