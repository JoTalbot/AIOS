#!/usr/bin/env python3
import sys, asyncio
from playwright.async_api import async_playwright

JS = """
() => {
  const res = [];
  const frames = document.querySelectorAll('iframe');
  frames.forEach((f, fi) => {
    let doc = null;
    try { doc = f.contentDocument; } catch(e) {}
    if (!doc) return;
    const areas = doc.querySelectorAll('pre, .output_area, .output_subarea');
    areas.forEach(a => { const t = (a.innerText||'').trim(); if (t) res.push('['+fi+'] '+t.slice(0,300)); });
  });
  // также текстовые ячейки в главном документе
  const main = document.querySelectorAll('div.output_area pre, div.output_subarea pre');
  main.forEach(a => { const t=(a.innerText||'').trim(); if(t) res.push('[main] '+t.slice(0,300)); });
  return res.join('\\n');
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
    out = await page.evaluate(JS)
    print(out if out else "(вывод пока пуст / не отрисован)")
    await p.stop()

asyncio.run(main())
