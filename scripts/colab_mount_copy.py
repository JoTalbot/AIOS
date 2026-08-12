#!/usr/bin/env python3
"""Смонтировать Google Drive и скопировать /content/models -> MyDrive/AIOS_colab_models."""
import asyncio
from playwright.async_api import async_playwright
CDP="http://localhost:9222"

CMD = r"""
import os, shutil
from google.colab import drive
if not os.path.isdir(/content/drive/MyDrive):
    drive.mount(/content/drive)
dst=/content/drive/MyDrive/AIOS_colab_models
os.makedirs(dst, exist_ok=True)
src=/content/models
if os.path.isdir(src):
    for f in os.listdir(src):
        shutil.copy2(os.path.join(src,f), os.path.join(dst,f))
print(DRIVE_COPY_DONE, sorted(os.listdir(dst)) if os.path.isdir(dst) else NO_DST)
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

async def allow_drive(browser):
    for ctx in browser.contexts:
        for pg in ctx.pages:
            try:
                u=pg.url
            except: u=""
            if "oauth" in u or "accounts.google" in u or "drive" in u:
                try:
                    for txt in ["Дозволити","Разрешить","Allow","Дозволити доступ","Дозволити цьому"]:
                        try:
                            loc=pg.get_by_role("button", name=txt)
                            if await loc.count()>0:
                                await loc.first.click(timeout=2000)
                                print("allow:",txt); await asyncio.sleep(6); return
                        except Exception: pass
                except Exception: pass

async def main():
    p=await async_playwright().start()
    b=await p.chromium.connect_over_cdp(CDP)
    ctx=b.contexts[0]
    page=None
    for pg in ctx.pages:
        try:
            if "Quant_ML_Training" in pg.url: page=pg; break
        except: pass
    if not page:
        print("вкладка не найдена"); await p.stop(); return
    print("Добавляю ячейку mount+copy...")
    await new_cell_and_run(page, CMD)
    # несколько раундов подтверждения доступа к Drive
    for i in range(4):
        await asyncio.sleep(8)
        await allow_drive(b)
        await asyncio.sleep(4)
    print("mount+copy запущен")
    await p.stop()
asyncio.run(main())
