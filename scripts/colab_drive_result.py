#!/usr/bin/env python3
import sys, asyncio
from playwright.async_api import async_playwright
async def main():
    nb_key=sys.argv[1] if len(sys.argv)>1 else "AIOS_Colab_Quant_ML_Training"
    p=await async_playwright().start()
    b=await p.chromium.connect_over_cdp("http://localhost:9222")
    ctx=b.contexts[0]
    for pg in ctx.pages:
        if nb_key in pg.url:
            # реальный вывод всех output-областей
            res=await pg.evaluate("""
              () => {
                const out=[];
                document.querySelectorAll('.output_area, .output_stream, .output_subarea, .output_result').forEach(o=>{
                  const t=(o.innerText||'').trim();
                  if(t && out.indexOf(t)<0) out.push(t.slice(0,200));
                });
                return out;
              }
            """)
            print("=== РЕАЛЬНЫЙ ВЫВОД ===")
            for r in res[-10:]:
                print(" •", r)
            break
    await p.stop()
asyncio.run(main())
