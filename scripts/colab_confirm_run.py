#!/usr/bin/env python3
"""Точно нажать 'Усе одно запустити' / 'Run anyway' в диалоге Colab."""
import sys, asyncio, json
from playwright.async_api import async_playwright

JS = r"""
() => {
  const EXACT = ["Усе одно запустити","Усе одно запустить","Всё равно запустить","Все равно запустить","Run anyway"];
  const EXACT_LOWER = EXACT.map(function(s){return s.toLowerCase();});
  let clicked=null;
  const tryClick=function(el){
    const t=(el.innerText||el.textContent||"").trim();
    const tl=t.toLowerCase();
    if(EXACT_LOWER.indexOf(tl)>=0){ el.click(); return t; }
    return null;
  };
  const walk=function(root){
    root.querySelectorAll("*").forEach(function(el){
      if(clicked) return;
      if(el.shadowRoot) walk(el.shadowRoot);
      const r=tryClick(el);
      if(r) clicked=r;
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
    nb_key = sys.argv[1] if len(sys.argv) > 1 else "AIOS_Colab_Quant_ML_Training"
    p = await async_playwright().start()
    b = await p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = b.contexts[0]
    page = None
    for pg in ctx.pages:
        if nb_key in pg.url:
            page = pg
            break
    if not page:
        print("вкладка не найдена")
        await p.stop()
        return
    print("Клик по:", await page.evaluate(JS))
    await asyncio.sleep(10)
    body = await page.evaluate("() => document.body.innerText")
    print("Диалог ещё есть:", "Усе одно запустити" in body)
    await p.stop()

if __name__ == "__main__":
    asyncio.run(main())
