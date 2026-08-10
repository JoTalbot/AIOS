#!/usr/bin/env python3
"""Отправить модели из Colab на VPS-приёмник через trycloudflare URL."""
import sys, asyncio
from playwright.async_api import async_playwright
CDP="http://localhost:9222"
TUNNEL="https://interracial-indicating-previously-fairly.trycloudflare.com"
CODE = r"""
import os, requests
url = '''' + TUNNEL + '/upload'''
mods=[]
for root,dirs,files in os.walk('/content/models'):
    for f in files:
        mods.append(os.path.join(root,f))
print('SEND_COUNT', len(mods))
for p in mods:
    name=os.path.basename(p)
    with open(p,'rb') as fh:
        r=requests.post(url, params={'name':name}, data=fh, timeout=180)
    print('SEND', name, r.status_code, r.text.strip()[:50])
print('SEND_DONE')
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
    print("Отправка моделей на VPS запущена")
    await asyncio.sleep(15)
    await p.stop()
asyncio.run(main())
