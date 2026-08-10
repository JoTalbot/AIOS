#!/usr/bin/env python3
"""Открыть ноутбук, выполнить drive.mount() (Colab API) и обработать OAuth."""
import sys, asyncio, re
from playwright.async_api import async_playwright

NB="https://colab.research.google.com/github/JoTalbot/AIOS/blob/main/docs/AIOS_Colab_Quant_ML_Training.ipynb"
CDP="http://localhost:9222"

MOUNT = r"""
from google.colab import drive
drive.mount('/content/drive')
print('MOUNT_OK')
"""

JS_CONFIRM = r"""
() => {
  const EXACT=["Усе одно запустити","Усе одно запустить","Всё равно запустить","Все равно запустить","Run anyway"];
  const L=EXACT.map(function(s){return s.toLowerCase();});
  let hit=null;
  const walk=function(root){
    root.querySelectorAll("*").forEach(function(el){
      if(hit) return;
      if(el.shadowRoot) walk(el.shadowRoot);
      const t=(el.innerText||el.textContent||"").trim();
      if(L.indexOf(t.toLowerCase())>=0){ el.click(); hit=t; }
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
    p=await async_playwright().start()
    b=await p.chromium.connect_over_cdp(CDP)
    ctx=b.contexts[0]
    page=None
    for pg in ctx.pages:
        if "Quant_ML_Training" in pg.url: page=pg; break
    if not page:
        page=await ctx.new_page()
        await page.set_viewport_size({"width":1400,"height":900})
        await page.goto(NB, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(10)
    await page.bring_to_front()
    # прервать возможное выполнение
    await page.keyboard.press("Control+m"); await page.keyboard.press("i")
    await asyncio.sleep(2)
    await page.mouse.click(500,400)
    await asyncio.sleep(1)
    await page.keyboard.press("Control+m"); await page.keyboard.press("b")
    await asyncio.sleep(1)
    # вставить mount код через clipboard
    await page.evaluate("(t)=>navigator.clipboard.writeText(t)", MOUNT)
    await asyncio.sleep(1)
    await page.keyboard.press("Control+v")
    await asyncio.sleep(1)
    await page.keyboard.press("Shift+Enter")
    print("drive.mount запущен")
    await asyncio.sleep(10)
    # подтвердить диалог доступа к Drive
    try:
        hit=await page.evaluate(JS_CONFIRM) or await page.evaluate(r"""
        () => {
          const L=["Підключитися до Google Диска","Connect to Google Drive","Подключиться к Google Диску","Продолжить"];
          const ll=L.map(s=>s.toLowerCase());
          let h=null;
          const w=(root)=>{root.querySelectorAll("*").forEach(el=>{
            if(h) return; if(el.shadowRoot) w(el.shadowRoot);
            const t=(el.innerText||"").trim();
            if(ll.indexOf(t.toLowerCase())>=0){el.click();h=t;}
          });};
          w(document);
          document.querySelectorAll("iframe").forEach(f=>{if(h)return;try{if(f.contentDocument)w(f.contentDocument);}catch(e){}});
          return h;
        }
        """)
        print("Клик по диалогу:", hit)
    except Exception as e:
        print("confirm err", e)
    await asyncio.sleep(8)
    # проверить oauth вкладки
    for pg in ctx.pages:
        if "signin/oauth" in pg.url or "consentsummary" in pg.url:
            print("OAuth-вкладка:", pg.url[:70])
    await p.stop()

asyncio.run(main())
