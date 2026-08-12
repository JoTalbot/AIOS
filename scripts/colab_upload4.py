#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright
CDP="http://localhost:9222"
TUNNEL="https://aims-style-jade-century.trycloudflare.com"
CMD = """import os, urllib.request, urllib.parse
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
async def main():
    p=await async_playwright().start()
    b=await p.chromium.connect_over_cdp(CDP)
    ctx=b.contexts[0]
    # список вкладок
    print("PAGES:")
    for pg in ctx.pages:
        try:
            print("  -", pg.url[:70])
        except: pass
    page=None
    for pg in ctx.pages:
        try:
            if "Quant_ML_Training" in pg.url: page=pg; break
        except: pass
    if not page: print("NO_TAB"); await p.stop(); return
    # 1. фокус на Colab
    await page.bring_to_front()
    await asyncio.sleep(3)
    # 2. клик в область ноутбука
    await page.mouse.click(900, 400)
    await asyncio.sleep(2)
    # 3. добавить ячейку
    await page.keyboard.press("Control+m")
    await page.keyboard.press("b")
    await asyncio.sleep(2)
    # 4. ввести код
    await page.keyboard.type(CMD, delay=1)
    await asyncio.sleep(2)
    # 5. выполнить (Shift+Enter)
    await page.keyboard.press("Shift+Enter")
    print("EXEC_SENT")
    await asyncio.sleep(20)
    await p.stop()
asyncio.run(main())
