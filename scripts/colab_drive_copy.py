#!/usr/bin/env python3
"""Смонтировать Drive и скопировать модели; затем обработать OAuth."""
import sys, asyncio, re
from playwright.async_api import async_playwright

CDP="http://localhost:9222"
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
print('DRIVE_COPY_DONE', sorted(os.listdir(dst)) if os.path.isdir(dst) else 'NO_DST')
"""

async def main():
    p=await async_playwright().start()
    b=await p.chromium.connect_over_cdp(CDP)
    ctx=b.contexts[0]
    page=None
    for pg in ctx.pages:
        if "Quant_ML_Training" in pg.url: page=pg; break
    if not page: print("вкладка не найдена"); await p.stop(); return
    await page.bring_to_front()
    await page.mouse.click(500,400)
    await asyncio.sleep(1)
    await page.keyboard.press("Control+m"); await page.keyboard.press("b")
    await asyncio.sleep(1)
    await page.keyboard.type(DRIVE, delay=1)
    await asyncio.sleep(1)
    await page.keyboard.press("Shift+Enter")
    print("mount Drive запущен")
    await asyncio.sleep(10)
    # найдём oauth popup
    for pg in ctx.pages:
        if "signin/oauth" in pg.url or "accounts.google.com" in pg.url and "signin" in pg.url:
            print("OAuth-вкладка:", pg.url[:80])
    await p.stop()

asyncio.run(main())
