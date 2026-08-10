#!/usr/bin/env python3
"""Разрешить доступ в OAuth окне Google."""
import sys, asyncio, json
from playwright.async_api import async_playwright
CDP="http://localhost:9222"
async def main():
    p=await async_playwright().start()
    b=await p.chromium.connect_over_cdp(CDP)
    ctx=b.contexts[0]
    page=None
    for pg in ctx.pages:
        if "signin/oauth" in pg.url:
            page=pg; break
    if not page:
        print("oauth вкладка не найдена"); await p.stop(); return
    await page.bring_to_front()
    await page.set_viewport_size({"width":800,"height":800})
    await asyncio.sleep(3)
    body=await page.evaluate("() => document.body.innerText")
    print("=== OAuth содержимое ===")
    print(body[:600])
    # ищем кнопки
    btns=await page.evaluate("""
      () => {
        const out=[];
        document.querySelectorAll("button, [role=button]").forEach(b=>{
          const t=(b.innerText||b.textContent||"").trim();
          if(t && t.length<40 && out.indexOf(t)<0) out.push(t);
        });
        return out;
      }
    """)
    print("Кнопки:", json.dumps(btns, ensure_ascii=False))
    await page.screenshot(path="/root/AIOS/data/oauth_allow.png")
    print("shot saved")
    await p.stop()
asyncio.run(main())
