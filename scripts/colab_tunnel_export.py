#!/usr/bin/env python3
"""Прервать текущую ячейку и запустить экспорт моделей через trycloudflare-туннель."""
import sys, asyncio
from playwright.async_api import async_playwright

CODE = r'''
import subprocess, re, os, time
os.makedirs('/content/models', exist_ok=True)
# список моделей
print('MODELS:', os.listdir('/content/models'))
# HTTP-сервер на /content
server = subprocess.Popen(['python','-m','http.server','8000','--directory','/content'],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
# cloudflared
subprocess.run(['pip','install','-q','cloudflared'], check=True)
tunnel = subprocess.Popen(['cloudflared','tunnel','--url','http://localhost:8000'],
                          stderr=subprocess.PIPE, text=True)
for line in iter(tunnel.stderr.readline, ''):
    m = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
    if m:
        print('TUNNEL_URL=' + m.group(0))
        break
'''

async def main():
    nb_key = sys.argv[1] if len(sys.argv)>1 else "AIOS_Colab_Quant_ML_Training"
    p=await async_playwright().start()
    b=await p.chromium.connect_over_cdp("http://localhost:9222")
    ctx=b.contexts[0]
    page=None
    for pg in ctx.pages:
        if nb_key in pg.url: page=pg; break
    if not page: print("вкладка не найдена"); await p.stop(); return
    await page.bring_to_front()
    # прервать выполнение (Ctrl+M I = interrupt)
    await page.keyboard.press("Control+m")
    await page.keyboard.press("i")
    await asyncio.sleep(1)
    # новая ячейка кода
    await page.keyboard.press("Control+m")
    await page.keyboard.press("b")
    await asyncio.sleep(1)
    await page.keyboard.type(CODE, delay=1)
    await asyncio.sleep(1)
    await page.keyboard.press("Shift+Enter")
    print("Туннель-экспорт запущен")
    await asyncio.sleep(6)
    await p.stop()

asyncio.run(main())
