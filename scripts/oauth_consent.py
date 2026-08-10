#!/usr/bin/env python3
"""Прочитать consent-summary и нажать разрешение."""
import sys, asyncio, json
from playwright.async_api import async_playwright
CDP="http://localhost:9222"
async def main():
    p=await async_playwright().start()
    b=await p.chromium.connect_over_cdp(CDP)
    ctx=b.contexts[0]
    page=None
    for pg in ctx.pages:
        if "consentsummary" in pg.url: page=pg; break
    if not page:
        print("consent вкладка не найдена")
        for pg in ctx.pages:
            if "oauth" in pg.url: print(" - oauth:", pg.url[:60])
        await p.stop(); return
    await page.bring_to_front()
    await page.set_viewport_size({"width":800,"height":900})
    await asyncio.sleep(3)
    body=await page.evaluate("() => document.body.innerText")
    print("=== consent ===")
    print(body[:700])
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
    await page.screenshot(path="/root/AIOS/data/consent.png")
    print("shot saved")
    await p.stop()
asyncio.run(main())
