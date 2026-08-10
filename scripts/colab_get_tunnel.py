#!/usr/bin/env python3
import sys, asyncio, re
from playwright.async_api import async_playwright
async def main():
    nb_key = sys.argv[1] if len(sys.argv)>1 else "AIOS_Colab_Quant_ML_Training"
    p=await async_playwright().start()
    b=await p.chromium.connect_over_cdp("http://localhost:9222")
    ctx=b.contexts[0]
    for pg in ctx.pages:
        if nb_key in pg.url:
            body=await pg.evaluate("() => document.body.innerText")
            # ищем TUNNEL_URL и MODELS
            m=re.search(r'TUNNEL_URL=\s*(https://[a-zA-Z0-9-]+\.trycloudflare\.com)', body)
            if m: print("TUNNEL_URL:", m.group(1))
            else:
                print("TUNNEL_URL не найден. Поиск trycloudflare...")
                mm=re.findall(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', body)
                print("найденные trycloudflare:", mm[:3])
            # MODELS
            for kw in ["MODELS:", "Installing", "Downloading", "cloudflared", "error", "Error"]:
                if kw.lower() in body.lower():
                    i=body.lower().find(kw.lower())
                    print(f"[{kw}] ...{body[max(0,i-40):i+120]!r}")
            break
    await p.stop()
asyncio.run(main())
