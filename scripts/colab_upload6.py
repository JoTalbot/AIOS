#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright
CDP="http://localhost:9222"
TUNNEL="https://aims-style-jade-century.trycloudflare.com"
# однострочный код - без отступов, не ломается при вводе
ONELINER = (
  "import os,urllib.request,urllib.parse;"
  "base=%r;"
  "src=\"/content/models\";"
  "[urllib.request.urlopen(urllib.request.Request(base+\"/upload?name=\"+urllib.parse.quote(f),data=open(os.path.join(src,f),\"rb\").read(),method=\"POST\"),timeout=90).read() for f in os.listdir(src) if os.path.isfile(os.path.join(src,f))];"
  "print(\"UPLOAD_DONE\")"
) % TUNNEL
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
    await page.bring_to_front()
    await asyncio.sleep(3)
    await page.mouse.click(900,400)
    await asyncio.sleep(1)
    await page.keyboard.press("Control+a")
    await asyncio.sleep(1)
    await page.keyboard.press("Delete")
    await asyncio.sleep(1)
    await page.keyboard.type(ONELINER, delay=0)
    await asyncio.sleep(2)
    await page.keyboard.press("Control+Enter")
    print("EXEC_SENT")
    await asyncio.sleep(25)
    await p.stop()
asyncio.run(main())
