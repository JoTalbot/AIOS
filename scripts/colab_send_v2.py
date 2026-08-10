#!/usr/bin/env python3
"""Отправить модели через однострочный base64 python -c."""
import sys, asyncio
from playwright.async_api import async_playwright
CDP="http://localhost:9222"
CMD = """!python -c "import base64;exec(base64.b64decode('CmltcG9ydCBvcywgcmVxdWVzdHMsIGdsb2IKdXJsID0gImh0dHBzOi8vaW50ZXJyYWNpYWwtaW5kaWNhdGluZy1wcmV2aW91c2x5LWZhaXJseS50cnljbG91ZGZsYXJlLmNvbS91cGxvYWQiCm1vZHMgPSBnbG9iLmdsb2IoIi9jb250ZW50L21vZGVscy8qIikKcHJpbnQoIlNFTkRfQ09VTlQiLCBsZW4obW9kcykpCmZvciBwIGluIG1vZHM6CiAgICBuYW1lID0gb3MucGF0aC5iYXNlbmFtZShwKQogICAgd2l0aCBvcGVuKHAsICJyYiIpIGFzIGZoOgogICAgICAgIHIgPSByZXF1ZXN0cy5wb3N0KHVybCwgcGFyYW1zPXsibmFtZSI6IG5hbWV9LCBkYXRhPWZoLCB0aW1lb3V0PTE4MCkKICAgIHByaW50KCJTRU5EIiwgbmFtZSwgci5zdGF0dXNfY29kZSwgci50ZXh0LnN0cmlwKClbOjQwXSkKcHJpbnQoIlNFTkRfRE9ORSIpCg=='))"""
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
    # вставить команду через clipboard
    await page.evaluate("(t)=>navigator.clipboard.writeText(t)", CMD)
    await asyncio.sleep(1)
    await page.keyboard.press("Control+v")
    await asyncio.sleep(1)
    await page.keyboard.press("Shift+Enter")
    print("однострочная отправка запущена")
    await asyncio.sleep(15)
    await p.stop()
asyncio.run(main())
