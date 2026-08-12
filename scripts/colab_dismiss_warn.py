#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright
CDP="http://localhost:9222"
# клик по кнопке через частичное совпадение текста, включая shadow DOM
JS = """
() => {
  const KEY="усе одно запустити";
  let h=null;
  const walk=function(root){
    if(!root) return;
    const q=(root.querySelectorAll||function(){return[];}).bind(root);
    q("button,paper-button,mwc-button,[role=button]").forEach(function(el){
      if(h) return;
      const t=(el.innerText||el.textContent||"").trim().toLowerCase();
      if(t && t.indexOf("усе одно")>=0 && t.indexOf("запустити")>=0){ el.click(); h=el.innerText; }
    });
  };
  const all=[document];
  const walkAll=function(){
    for(let i=0;i<all.length;i++){
      const r=all[i];
      walk(r);
      if(r.querySelectorAll){
        r.querySelectorAll("*").forEach(function(e){ if(e.shadowRoot) all.push(e.shadowRoot); });
      }
    }
  };
  walkAll();
  return h;
}
"""
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
    for i in range(3):
        try:
            hit=await page.evaluate(JS)
            print("dismiss", i, "hit:", hit)
            if hit: await asyncio.sleep(3); break
        except Exception as e:
            print("err", str(e)[:80])
        await asyncio.sleep(2)
    await page.screenshot(path="/tmp/dismissed.png")
    await p.stop()
asyncio.run(main())
