#!/usr/bin/env python3
"""Нажать кнопку 'Дозволити' в диалоге доступа к Google Диску."""
import sys, asyncio
from playwright.async_api import async_playwright
CDP="http://localhost:9222"
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
    await asyncio.sleep(1)
    clicked=False
    # ищем кнопки Разрешить/Дозволити/Allow
    for txt in ["Дозволити","Разрешить","Allow","Дозволити доступ","Підключитися","Дозволити цьому"]:
        try:
            loc=page.get_by_role("button", name=txt) if txt not in ("Дозволити","Разрешить") else page.get_by_role("button", name=txt)
            if await loc.count()>0:
                await loc.first.click(timeout=3000)
                print("👍 Клик по кнопке:", txt)
                clicked=True; break
        except Exception:
            continue
    if not clicked:
        # fallback: JS точный
        js="""() => {
          const EXACT=["Дозволити","Разрешить","Allow","Дозволити доступ"];
          const L=EXACT.map(function(s){return s.toLowerCase();});
          let h=null;
          const w=function(root){
            root.querySelectorAll("button,paper-button,mwc-button,[role=button],colab-button").forEach(function(el){
              if(h) return;
              if(el.shadowRoot) w(el.shadowRoot);
              const t=(el.innerText||el.textContent||"").trim();
              if(L.indexOf(t.toLowerCase())>=0){ el.click(); h=t; }
            });
          };
          w(document);
          document.querySelectorAll("iframe").forEach(function(f){
            if(h) return;
            try{ if(f.contentDocument) w(f.contentDocument);}catch(e){}
          });
          return h;
        }"""
        print("Клик(JS):", await page.evaluate(js))
        clicked=True
    await asyncio.sleep(10)
    # проверить oauth вкладку
    for pg in ctx.pages:
        if "signin/oauth" in pg.url:
            print("OAuth-вкладка:", pg.url[:90])
    await p.stop()
asyncio.run(main())
