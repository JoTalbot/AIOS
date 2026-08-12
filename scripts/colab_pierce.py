#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright
CDP="http://localhost:9222"
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
    await page.bring_to_front(); await asyncio.sleep(2)
    # 1) попробовать проникнуть в shadow DOM через locator с pierce
    candidates = [
        "button:has-text(усе одно запустити)",
        "button:has-text(все одно запустити)",
        "button:has-text(Все равно запустить)",
        "button:has-text(Всё равно запустить)",
        "button:has-text(Запустить)",
        "button:has-text(запустити)",
        "text=усе одно запустити",
        "text=все одно запустити",
        "text=Запустить",
    ]
    clicked=False
    for sel in candidates:
        try:
            loc=page.locator(sel)
            if await loc.count()>0 and await loc.first.is_visible():
                await loc.first.click(timeout=3000)
                print("CLICKED:", sel)
                clicked=True
                await asyncio.sleep(4)
                break
        except Exception as e:
            print("skip", sel, str(e)[:40])
    if not clicked:
        print("NO_BUTTON_FOUND - dump buttons")
        try:
            btns=await page.evaluate("""() => {
              const out=[];
              const w=(r)=>{ if(!r)return; (r.querySelectorAll(button,[role=button],paper-button,mwc-button)||[]).forEach(e=>out.push((e.innerText||e.textContent||).trim())); if(r.querySelectorAll) r.querySelectorAll(*).forEach(x=>{if(x.shadowRoot)w(x.shadowRoot)}); };
              w(document); return out.filter(t=>t && t.length<40);
            }""")
            for b in btns[:30]: print("BTN:", repr(b))
        except Exception as e:
            print("dump err", str(e)[:60])
    await p.stop()
asyncio.run(main())
