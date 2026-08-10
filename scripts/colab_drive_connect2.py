#!/usr/bin/env python3
"""Точно кликнуть кнопку подключения Google Диска."""
import sys, asyncio
from playwright.async_api import async_playwright
CDP="http://localhost:9222"
JS = r"""
() => {
  const targets=["Підключитися до Google Диска","Connect to Google Drive","Підключитись до Google Диска","Подключиться к Google Диску"];
  const L=targets.map(function(s){return s.toLowerCase();});
  let hit=null;
  const tryEl=function(el){
    const t=(el.innerText||el.textContent||"").trim();
    if(L.indexOf(t.toLowerCase())>=0){ el.click(); return t; }
    return null;
  };
  const walk=function(root){
    root.querySelectorAll("button, span, div, mwc-button, paper-button, [role=button]").forEach(function(el){
      if(hit) return;
      if(el.shadowRoot) walk(el.shadowRoot);
      const r=tryEl(el);
      if(r) hit=r;
    });
  };
  walk(document);
  document.querySelectorAll("iframe").forEach(function(f){
    if(hit) return;
    try{ if(f.contentDocument) walk(f.contentDocument);}catch(e){}
  });
  return hit;
}
"""
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
    await asyncio.sleep(2)
    print("Клик:", await page.evaluate(JS))
    await asyncio.sleep(8)
    for pg in ctx.pages:
        if "signin/oauth" in pg.url:
            print("OAuth-вкладка:", pg.url[:80])
    await p.stop()
asyncio.run(main())
