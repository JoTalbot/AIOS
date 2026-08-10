#!/usr/bin/env python3
import sys, asyncio
from playwright.async_api import async_playwright

async def main():
    nb_key = sys.argv[1] if len(sys.argv) > 1 else "AIOS_Colab_Quant_ML_Training"
    p = await async_playwright().start()
    b = await p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = b.contexts[0]
    page = None
    for pg in ctx.pages:
        if nb_key in pg.url: page = pg; break
    if not page:
        print("вкладка не найдена"); await p.stop(); return
    # фокус на страницу и Enter
    await page.bring_to_front()
    await page.mouse.move(960, 500)
    await page.mouse.click(960, 500)
    await asyncio.sleep(1)
    await page.keyboard.press("Enter")
    await asyncio.sleep(2)
    await page.keyboard.press("Enter")
    await asyncio.sleep(8)
    # проверим, исчез ли диалог
    body = await page.evaluate("() => document.body.innerText")
    has = "Усе одно запустити" in body or "Run anyway" in body
    print("Диалог подтверждения всё ещё есть:", has)
    # проверим наличие вывода (модели/epoch)
    print("Epoch в тексте:", "epoch" in body.lower())
    print("ХВОСТ:")
    print(body[-300:])
    await p.stop()

asyncio.run(main())
