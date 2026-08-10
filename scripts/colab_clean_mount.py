#!/usr/bin/env python3
"""Прервать выполнение, смонтировать Drive чисто."""
import sys, asyncio
from playwright.async_api import async_playwright
CDP="http://localhost:9222"
MOUNT = r"""
from google.colab import drive
drive.mount('/content/drive')
print('MOUNT_DONE_MARKER')
"""
async def main():
    nb_key=sys.argv[1] if len(sys.argv)>1 else "AIOS_Colab_Quant_ML_Training"
    p=await async_playwright().start()
    b=await p.chromium.connect_over_cdp(CDP)
    ctx=b.contexts[0]
    page=None
    for pg in ctx.pages:
        if nb_key in pg.url: page=pg; break
    if not page: print("вкладка не найдена"); await p.stop(); return
    await page.bring_to_front()
    # interrupt выполнение
    await page.keyboard.press("Control+m"); await page.keyboard.press("i")
    await asyncio.sleep(3)
    # новая чистая ячейка
    await page.mouse.click(500,400)
    await asyncio.sleep(1)
    await page.keyboard.press("Control+m"); await page.keyboard.press("b")
    await asyncio.sleep(1)
    await page.keyboard.type(MOUNT, delay=1)
    await asyncio.sleep(1)
    await page.keyboard.press("Shift+Enter")
    print("mount запущен (чистый)")
    await asyncio.sleep(10)
    # проверим oauth
    for pg in ctx.pages:
        if "consentsummary" in pg.url or "signin/oauth" in pg.url:
            print("OAuth-вкладка:", pg.url[:70])
    await p.stop()
asyncio.run(main())
