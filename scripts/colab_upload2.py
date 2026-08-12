#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright
CDP="http://localhost:9222"
TUNNEL="https://aims-style-jade-century.trycloudflare.com"
CMD = """
import os, urllib.request, urllib.parse
base="%TUNNEL%"
src="/content/models"
print("MODELS_SRC", src, os.path.isdir(src))
if os.path.isdir(src):
    for f in sorted(os.listdir(src)):
        p=os.path.join(src,f)
        if os.path.isfile(p):
            data=open(p,"rb").read()
            url=base+"/upload?name="+urllib.parse.quote(f)
            req=urllib.request.Request(url, data=data, method="POST")
            try:
                resp=urllib.request.urlopen(req, timeout=90)
                print("UPLOAD_OK", f, len(data), resp.read().decode())
            except Exception as e:
                print("UPLOAD_ERR", f, repr(e)[:150])
print("UPLOAD_DONE")
""".replace("%TUNNEL%", TUNNEL)
async def new_cell_and_run(page, code):
    await page.bring_to_front()
    await asyncio.sleep(1)
    await page.keyboard.press("Control+End")
    await asyncio.sleep(1)
    await page.keyboard.press("Control+m"); await page.keyboard.press("b")
    await asyncio.sleep(1)
    await page.keyboard.type(code, delay=0)
    await asyncio.sleep(1)
    await page.keyboard.press("Shift+Enter")
    await asyncio.sleep(15)
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
    for kw in ["MODELS_SRC","UPLOAD_OK","UPLOAD_ERR","UPLOAD_DONE"]:
        i=body.rfind(kw)
        if i>=0:
            print("==%s=="%kw, body[max(0,i-5):i+120].replace("\xa0"," ").replace("\n"," ")[:160])
    await p.stop()
asyncio.run(main())
