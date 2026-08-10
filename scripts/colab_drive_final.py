#!/usr/bin/env python3
"""Открыть ноутбук Quant ML, проверить модели, смонтировать Drive и скопировать модели."""
import sys, asyncio, re
from playwright.async_api import async_playwright

NB = "https://colab.research.google.com/github/JoTalbot/AIOS/blob/main/docs/AIOS_Colab_Quant_ML_Training.ipynb"
CDP = "http://localhost:9222"

CHECK = r"""
import os
print('RUNTIME_ALIVE')
print('MODELS_EXIST', os.path.isdir('/content/models'))
if os.path.isdir('/content/models'):
    print('MODEL_FILES', sorted(os.listdir('/content/models')))
"""

DRIVE = r"""
import os, shutil
from google.colab import drive
drive.mount('/content/drive')
src='/content/models'
dst='/content/drive/MyDrive/AIOS_colab_models'
os.makedirs(dst, exist_ok=True)
if os.path.isdir(src):
    for f in os.listdir(src):
        shutil.copy2(os.path.join(src,f), os.path.join(dst,f))
print('DRIVE_COPY_DONE', os.listdir(dst))
"""

async def new_cell_and_run(page, code):
    await page.bring_to_front()
    await page.mouse.click(400,300)
    await asyncio.sleep(1)
    await page.keyboard.press("Control+m")
    await page.keyboard.press("b")
    await asyncio.sleep(1)
    await page.keyboard.type(code, delay=1)
    await asyncio.sleep(1)
    await page.keyboard.press("Shift+Enter")
    await asyncio.sleep(4)

async def main():
    p=await async_playwright().start()
    b=await p.chromium.connect_over_cdp(CDP)
    ctx=b.contexts[0]

    # найти или открыть вкладку
    page=None
    for pg in ctx.pages:
        if "Quant_ML_Training" in pg.url: page=pg; break
    if not page:
        page=await ctx.new_page()
        await page.set_viewport_size({"width":1400,"height":900})
        print("Открываю ноутбук...")
        await page.goto(NB, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(8)
    else:
        print("Использую существующую вкладку")

    # подтвердить диалог запуска, если есть (но НЕ запускать все ячейки)
    # (просто чтобы убрать оверлей)
    try:
        await page.keyboard.press("Escape")
    except Exception: pass

    # добавить ячейку проверки моделей
    print("Запускаю проверку моделей...")
    await new_cell_and_run(page, CHECK)
    await asyncio.sleep(8)

    # читаем результат
    body=await page.evaluate("() => document.body.innerText")
    for kw in ["RUNTIME_ALIVE","MODELS_EXIST","MODEL_FILES"]:
        if kw in body:
            i=body.find(kw)
            print(f"  [{kw}] ...{body[max(0,i-20):i+120]!r}")
    await p.stop()

asyncio.run(main())
