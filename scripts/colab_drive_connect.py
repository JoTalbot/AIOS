#!/usr/bin/env python3
"""Нажать 'Підключитися до Google Диска' и обработать OAuth."""
import sys, asyncio
from playwright.async_api import async_playwright
CDP="http://localhost:9222"
JS = r"""
() => {
  const EXACT=["Підключитися до Google Диска","Підключитися","Connect to Google Drive","Подключиться к Google Диску","Разрешить","Дозволити"];
  const L=EXACT.map(function(s){return s.toLowerCase();});
  let hit=null;
  const walk=function(root){
    root.querySelectorAll("*").forEach(function(el){
      if(hit) return;
      if(el.shadowRoot) walk(el.shadowRoot);
      const t=(el.innerText||el.textContent||"").trim();
      if(L.indexOf(t.toLowerCase())>=0){ el.click(); hit=t; }
      else if(t.length<30 && /підключ|подключ|дозвол|разреш|connect|allow/i.test(t)){ el.click(); hit=t; }
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
    # проверить новые вкладки (oauth)
    for pg in ctx.pages:
        if "signin/oauth" in pg.url:
            print("OAuth-вкладка открыта:", pg.url[:80])
    await p.stop()
asyncio.run(main())
