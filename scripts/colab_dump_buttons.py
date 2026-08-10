#!/usr/bin/env python3
import sys, asyncio, json
from playwright.async_api import async_playwright
CDP="http://localhost:9222"
JS = r"""
() => {
  const out=[];
  const walk=function(root){
    root.querySelectorAll("*").forEach(function(el){
      if(el.shadowRoot) walk(el.shadowRoot);
      if(/button|role=button|colab-button/i.test(el.tagName+" "+(el.getAttribute&&el.getAttribute("role")||""))) {
        const t=(el.innerText||"").trim();
        if(t && t.length<60 && out.indexOf(t)<0) out.push(t);
      }
    });
  };
  walk(document);
  document.querySelectorAll("iframe").forEach(function(f){
    try{ if(f.contentDocument) walk(f.contentDocument);}catch(e){}
  });
  return out.slice(0,40);
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
    buttons=await page.evaluate(JS)
    print("Кнопки в диалоге:", json.dumps(buttons, ensure_ascii=False))
    # скриншот
    await page.screenshot(path="/root/AIOS/data/dialog.png")
    print("скриншот: dialog.png")
    await p.stop()
asyncio.run(main())
