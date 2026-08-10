#!/usr/bin/env python3
import sys, asyncio
from playwright.async_api import async_playwright

JS = r"""
() => {
  const EXACT = ["Скасувати","Отмена","Cancel","Отменить"];
  const L = EXACT.map(function(s){return s.toLowerCase();});
  let clicked=null;
  const walk=function(root){
    root.querySelectorAll("*").forEach(function(el){
      if(clicked) return;
      if(el.shadowRoot) walk(el.shadowRoot);
      const t=(el.innerText||el.textContent||"").trim();
      if(L.indexOf(t.toLowerCase())>=0){ el.click(); clicked=t; }
    });
  };
  walk(document);
  document.querySelectorAll("iframe").forEach(function(f){
    if(clicked) return;
    try{ if(f.contentDocument) walk(f.contentDocument);}catch(e){}
  });
  return clicked;
}
"""
async def main():
    nb_key = sys.argv[1] if len(sys.argv)>1 else "AIOS_Colab_Quant_ML_Training"
    p=await async_playwright().start()
    b=await p.chromium.connect_over_cdp("http://localhost:9222")
    ctx=b.contexts[0]
    page=None
    for pg in ctx.pages:
        if nb_key in pg.url: page=pg; break
    if not page: print("не найдена"); await p.stop(); return
    print("Клик по:", await page.evaluate(JS))
    await asyncio.sleep(6)
    body=await page.evaluate("() => document.body.innerText")
    print("Диалог перезапуска есть:", "Перезапустити сеанс" in body)
    await p.stop()
asyncio.run(main())
