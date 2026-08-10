#!/usr/bin/env python3
"""Прервать mount, загрузить модели в file.io/transfer.sh, вывести ссылки."""
import sys, asyncio
from playwright.async_api import async_playwright
CDP="http://localhost:9222"
CODE = r"""
import os, requests, time, json
models=[]
for root,dirs,files in os.walk('/content/models'):
    for f in files:
        models.append(os.path.join(root,f))
print('FILE_COUNT', len(models))
for p in models:
    name=os.path.basename(p)
    # transfer.sh (до 2GB, прямая загрузка по ссылке)
    try:
        with open(p,'rb') as fh:
            r=requests.put('https://transfer.sh/'+name, data=fh, timeout=120)
        if r.status_code==200:
            print('TRANSFER_LINK', name, r.text.strip())
            continue
    except Exception as e:
        print('transfer_sh_fail', name, str(e)[:60])
    # fallback file.io
    try:
        with open(p,'rb') as fh:
            r=requests.post('https://file.io', files={'file':(name,fh)}, timeout=120)
        d=r.json()
        if d.get('success'):
            print('FILEIO_LINK', name, d['link'])
    except Exception as e:
        print('fileio_fail', name, str(e)[:60])
print('DONE')
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
    await page.keyboard.press("Control+m"); await page.keyboard.press("i")
    await asyncio.sleep(3)
    await page.mouse.click(500,400)
    await asyncio.sleep(1)
    await page.keyboard.press("Control+m"); await page.keyboard.press("b")
    await asyncio.sleep(1)
    await page.keyboard.type(CODE, delay=1)
    await asyncio.sleep(1)
    await page.keyboard.press("Shift+Enter")
    print("Загрузка моделей в fileio/transfer запущена")
    await asyncio.sleep(15)
    await p.stop()
asyncio.run(main())
