#!/usr/bin/env python3
"""Прочитать реальный ВЫВОД ячейки (не source) + статус runtime."""
import sys, asyncio
from playwright.async_api import async_playwright
async def main():
    nb_key=sys.argv[1] if len(sys.argv)>1 else "AIOS_Colab_Quant_ML_Training"
    p=await async_playwright().start()
    b=await p.chromium.connect_over_cdp("http://localhost:9222")
    ctx=b.contexts[0]
    page=None
    for pg in ctx.pages:
        if nb_key in pg.url: page=pg; break
    if not page: print("вкладка не найдена"); await p.stop(); return
    # реальный вывод: ищем <pre> в output_area, не source
    res=await page.evaluate("""
      () => {
        const out=[];
        document.querySelectorAll('div.output_area, div.output_subarea, div.output_stream').forEach(o=>{
          const pre=o.querySelector('pre');
          const t=pre?pre.innerText:(o.innerText||'');
          if(t && t.trim()) out.push(t.trim());
        });
        return out.join('\\n===CELL===\\n');
      }
    """)
    print("=== ВЫВОД ЯЧЕЕК (output) ===")
    print(res[:1500] if res else "(вывод пуст)")
    # статус подключения
    body=await page.evaluate("() => document.body.innerText")
    conn = "Connected" in body or "Підключено" in body or "runtime" in body.lower()
    print("\n=== runtime подключён (признак):", conn)
    await p.stop()
asyncio.run(main())
