#!/usr/bin/env python3
"""Запустить mount Drive и извлечь URL авторизации."""
import sys, asyncio, re
from playwright.async_api import async_playwright

CODE = r"""
from google.colab import drive
drive.mount('/content/drive')
"""

async def main():
    nb_key = sys.argv[1] if len(sys.argv)>1 else "AIOS_Colab_Quant_ML_Training"
    p=await async_playwright().start()
    b=await p.chromium.connect_over_cdp("http://localhost:9222")
    ctx=b.contexts[0]
    page=None
    for pg in ctx.pages:
        if nb_key in pg.url: page=pg; break
    if not page: print("вкладка не найдена"); await p.stop(); return
    await page.bring_to_front()
    await page.mouse.click(400,300)
    await asyncio.sleep(1)
    # прервать текущую (туннельную) ячейку
    await page.keyboard.press("Control+m"); await page.keyboard.press("i")
    await asyncio.sleep(1)
    # новая ячейка
    await page.keyboard.press("Control+m"); await page.keyboard.press("b")
    await asyncio.sleep(1)
    await page.keyboard.type(CODE, delay=1)
    await asyncio.sleep(1)
    await page.keyboard.press("Shift+Enter")
    print("mount Drive запущен")
    await asyncio.sleep(6)
    await p.stop()

asyncio.run(main())
