#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright
CDP="http://localhost:9222"
import importlib.util
spec=importlib.util.spec_from_file_location("u","/root/AIOS/scripts/colab_upload10.py")
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
CMD=m.B64CMD
JS_CONFIRM = """
() => {
  const L=["усе одно запустити","все одно запустити","все равно запустить","всё равно запустить","run anyway","запустить","усе одно","все одно","все равно","всё равно"];
  let h=null;
  const walk=function(root){
    root.querySelectorAll("button,paper-button,mwc-button,[role=button],colab-button").forEach(function(el){
      if(h) return;
      if(el.shadowRoot) walk(el.shadowRoot);
      const t=(el.innerText||el.textContent||"").trim();
      if(L.indexOf(t.toLowerCase())>=0){ el.click(); h=t; }
    });
  };
  walk(document);
  document.querySelectorAll("iframe").forEach(function(f){ if(h) return; try{ if(f.contentDocument) walk(f.contentDocument);}catch(e){} });
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
    # подтвердить предупреждение
    try:
        hit=await page.evaluate(JS_CONFIRM)
        print("confirm hit:", hit)
        await asyncio.sleep(3)
    except Exception as e:
        print("confirm err", str(e)[:60])
    # добавить ячейку и вставить код
    await page.mouse.click(400,300); await asyncio.sleep(1)
    await page.keyboard.press("Control+m"); await page.keyboard.press("b"); await asyncio.sleep(2)
    await page.keyboard.insert_text(CMD); await asyncio.sleep(2)
    await page.keyboard.press("Shift+Enter")
    print("EXEC_SENT")
    # снова подтверждение (может появиться)
    await asyncio.sleep(3)
    try:
        hit=await page.evaluate(JS_CONFIRM)
        print("confirm2:", hit)
    except Exception as e:
        print("confirm2 err", str(e)[:60])
    await asyncio.sleep(25)
    await page.screenshot(path="/tmp/confirm_run.png")
    await p.stop()
asyncio.run(main())
