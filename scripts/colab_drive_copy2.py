#!/usr/bin/env python3
"""Скопировать модели в уже смонтированный Drive."""
import sys, asyncio
from playwright.async_api import async_playwright
CDP="http://localhost:9222"
CMD = r"""
!python -c "import os,shutil;os.makedirs('/content/drive/MyDrive/AIOS_colab_models',exist_ok=True);r=[shutil.copy2('/content/models/'+f,'/content/drive/MyDrive/AIOS_colab_models/'+f) for f in os.listdir('/content/models')];print('DRIVE_UPLOADED',os.listdir('/content/drive/MyDrive/AIOS_colab_models'))"
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
    await page.mouse.click(500,400)
    await asyncio.sleep(1)
    await page.keyboard.press("Control+m"); await page.keyboard.press("b")
    await asyncio.sleep(1)
    await page.keyboard.press("Control+a"); await page.keyboard.press("Delete")
    await asyncio.sleep(1)
    await page.keyboard.type(CMD, delay=0)
    await asyncio.sleep(1)
    await page.keyboard.press("Shift+Enter")
    print("Копирование моделей в Drive запущено")
    await asyncio.sleep(15)
    await p.stop()
asyncio.run(main())
