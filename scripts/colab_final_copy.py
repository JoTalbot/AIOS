#!/usr/bin/env python3
"""Финальная ячейка: проверить mount, скопировать модели, вывести результат."""
import sys, asyncio
from playwright.async_api import async_playwright
CDP="http://localhost:9222"
CODE = r"""
import os, shutil
print('=== AIOS_DRIVE_STATUS ===')
print('drive_mounted', os.path.isdir('/content/drive/MyDrive'))
src='/content/models'
print('models_dir', os.path.isdir(src))
if os.path.isdir(src):
    print('model_files', sorted(os.listdir(src)))
dst='/content/drive/MyDrive/AIOS_colab_models'
if os.path.isdir('/content/drive/MyDrive'):
    os.makedirs(dst, exist_ok=True)
    if os.path.isdir(src):
        for f in os.listdir(src):
            shutil.copy2(os.path.join(src,f), os.path.join(dst,f))
    print('AIOS_DRIVE_COPIED', sorted(os.listdir(dst)) if os.path.isdir(dst) else 'NO_DST')
else:
    print('DRIVE_NOT_MOUNTED')
print('=== END ===')
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
    await page.keyboard.type(CODE, delay=1)
    await asyncio.sleep(1)
    await page.keyboard.press("Shift+Enter")
    print("финальная ячейка запущена")
    await asyncio.sleep(12)
    await page.screenshot(path="/root/AIOS/data/drive_result.png")
    print("скриншот: drive_result.png")
    await p.stop()
asyncio.run(main())
