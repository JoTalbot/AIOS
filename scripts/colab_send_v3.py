#!/usr/bin/env python3
"""Однострочная отправка моделей (без отступов)."""
import sys, asyncio
from playwright.async_api import async_playwright
CDP="http://localhost:9222"
CMD = """!python -c "import os,requests,glob;r=[requests.post('https://interracial-indicating-previously-fairly.trycloudflare.com/upload',params={'name':os.path.basename(f)},data=open(f,'rb').read(),timeout=300) for f in glob.glob('/content/models/*')];print('SENT',[(os.path.basename(f),x.status_code) for f,x in zip(glob.glob('/content/models/*'),r)])"""
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
    # прервать выполнение
    await page.keyboard.press("Control+m"); await page.keyboard.press("i")
    await asyncio.sleep(2)
    await page.mouse.click(500,400)
    await asyncio.sleep(1)
    await page.keyboard.press("Control+m"); await page.keyboard.press("b")
    await asyncio.sleep(1)
    # удалить возможный вставленный текст (Select all + delete)
    await page.keyboard.press("Control+a"); await page.keyboard.press("Delete")
    await asyncio.sleep(1)
    await page.keyboard.type(CMD, delay=0)
    await asyncio.sleep(1)
    await page.keyboard.press("Shift+Enter")
    print("однострочная отправка запущена (v3)")
    await asyncio.sleep(15)
    await p.stop()
asyncio.run(main())
