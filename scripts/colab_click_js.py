#!/usr/bin/env python3
import sys, asyncio, json
from playwright.async_api import async_playwright

JS_CLICK = """
() => {
  const targets = ['Усе одно запустити','Усе одно','Все равно запустить','Всё равно запустить','Run anyway','Запустить','Выполнить'];
  let clicked = null;
  const tryClick = (el) => {
    const t = (el.innerText||el.textContent||'').trim();
    for (const tg of targets) {
      if (t === tg) {
        el.click();
        return tg;
      }
    }
    // кнопки, содержащие слово запустить (короче 40)
    if (t.length>0 && t.length<40 && /запуст|выполн|run/i.test(t)) {
      el.click();
      return t;
    }
    return null;
  };
  const walk = (root) => {
    root.querySelectorAll('*').forEach(el => {
      if (clicked) return;
      if (el.shadowRoot) walk(el.shadowRoot);
      const r = tryClick(el);
      if (r) clicked = r;
    });
  };
  walk(document);
  document.querySelectorAll('iframe').forEach(f => {
    if (clicked) return;
    try { if (f.contentDocument) walk(f.contentDocument); } catch(e){}
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
        if nb_key in pg.url: page = pg; break
    if not page:
        print("вкладка не найдена"); await p.stop(); return
    res = await page.evaluate(JS_CLICK)
    print("Клик по:", res)
    await asyncio.sleep(8)
    # проверка
    body = await page.evaluate("() => document.body.innerText")
    print("Диалог ещё есть:", "Усе одно запустити" in body)
    await p.stop()

asyncio.run(main())
