#!/usr/bin/env python3
"""Добавить и запустить ячейку монтирования Google Drive в текущей Colab-сессии."""
import sys, asyncio
from playwright.async_api import async_playwright

CODE = r'''
from google.colab import drive
drive.mount('/content/drive')
import shutil, os
src='/content/models'
dst='/content/drive/MyDrive/AIOS_colab_models'
os.makedirs(dst, exist_ok=True)
if os.path.exists(src):
    for f in os.listdir(src):
        shutil.copy2(os.path.join(src,f), os.path.join(dst,f))
print('DRIVE_COPY_DONE', os.listdir(dst))
'''

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
    await page.mouse.click(400,300)  # клик в область ноутбука
    await asyncio.sleep(1)
    # новая ячейка кода: Ctrl+M B
    await page.keyboard.press("Control+m")
    await page.keyboard.press("b")
    await asyncio.sleep(1)
    # ввести код
    await page.keyboard.type(CODE, delay=2)
    await asyncio.sleep(1)
    # запустить Shift+Enter
    await page.keyboard.press("Shift+Enter")
    print("Ячейка добавлена и запущена (mount Drive)")
    await asyncio.sleep(8)
    await p.stop()

asyncio.run(main())
