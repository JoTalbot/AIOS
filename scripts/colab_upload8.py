#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright
CDP="http://localhost:9222"
TUNNEL="https://aims-style-jade-century.trycloudflare.com"
ONELINER = "import os,urllib.request,urllib.parse\nbase=\"%s\"\nfor f in os.listdir(\"/content/models\"):\n    p=os.path.join(\"/content/models\",f)\n    if os.path.isfile(p):\n        urllib.request.urlopen(urllib.request.Request(base+\"/upload?name=\"+urllib.parse.quote(f),data=open(p,\"rb\").read(),method=\"POST\"),timeout=90)\nprint(\"UPLOAD_DONE\")\n" % TUNNEL
async def new_cell_and_run(page, code):
    await page.bring_to_front()
    await page.mouse.click(400,300)   # проверенный способ из colab_drive_final
    await asyncio.sleep(1)
    await page.keyboard.press("Control+m"); await page.keyboard.press("b")
    await asyncio.sleep(1)
    await page.keyboard.type(code, delay=1)
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
    await new_cell_and_run(page, ONELINER)
    body=await page.evaluate("() => document.body.innerText")
    i=body.rfind("UPLOAD_DONE")
    if i>=0:
        print("DONE_FOUND", body[max(0,i-100):i+60].replace("\xa0"," ").replace("\n"," ")[:180])
    else:
        print("UPLOAD_DONE_NOT_SEEN")
    await p.stop()
asyncio.run(main())
