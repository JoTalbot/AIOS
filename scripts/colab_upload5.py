#!/usr/bin/env python3
import asyncio, json
from playwright.async_api import async_playwright
CDP="http://localhost:9222"
TUNNEL="https://aims-style-jade-century.trycloudflare.com"
CMD = """import os, urllib.request, urllib.parse
base="%TUNNEL%"
src="/content/models"
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
    # выбрать всё и удалить в текущей ячейке (чтобы не плодить мусор)
    await page.mouse.click(900,400)
    await asyncio.sleep(1)
    await page.keyboard.press("Control+a")
    await asyncio.sleep(1)
    await page.keyboard.press("Delete")
    await asyncio.sleep(1)
    # вставить через clipboard
    await page.evaluate("navigator.clipboard.writeText(%s)" % json.dumps(CMD))
    await asyncio.sleep(1)
    await page.keyboard.press("Control+v")
    await asyncio.sleep(2)
    # выполнить текущую ячейку
    await page.keyboard.press("Control+Enter")
    print("EXEC_SENT")
    await asyncio.sleep(25)
    await p.stop()
asyncio.run(main())
