#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright
CDP="http://localhost:9222"
CMD = r"""
import os
print("DIR_DRIVE", os.path.isdir("/content/drive/MyDrive"))
dst="/content/drive/MyDrive/AIOS_colab_models"
print("DST", os.path.isdir(dst))
if os.path.isdir(dst):
    print("FILES", sorted(os.listdir(dst)))
print("MODELS", os.path.isdir("/content/models"))
if os.path.isdir("/content/models"):
    print("MODEL_FILES", sorted(os.listdir("/content/models")))
"""
async def new_cell_and_run(page, code):
    await page.bring_to_front()
    await page.mouse.click(400,300)
    await asyncio.sleep(1)
    await page.keyboard.press("Control+m"); await page.keyboard.press("b")
    await asyncio.sleep(1)
    await page.keyboard.type(code, delay=1)
    await asyncio.sleep(1)
    await page.keyboard.press("Shift+Enter")
    await asyncio.sleep(10)
async def main():
    p=await async_playwright().start()
    b=await p.chromium.connect_over_cdp(CDP)
    ctx=b.contexts[0]
    page=None
    for pg in ctx.pages:
        try:
            if "Quant_ML_Training" in pg.url: page=pg; break
        except: pass
    if not page: print("NO_TAB"); await p.stop(); return
    await new_cell_and_run(page, CMD)
    body=await page.evaluate("() => document.body.innerText")
    for kw in ["DIR_DRIVE","DST","FILES","MODELS","MODEL_FILES"]:
        i=body.find(kw)
        if i>=0:
            print(f"=={kw}==", body[max(0,i-5):i+140].replace("\\xa0"," ").replace("\\n"," ")[:160])
    await p.stop()
asyncio.run(main())
