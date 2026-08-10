#!/usr/bin/env python3
import sys, asyncio, json
from playwright.async_api import async_playwright

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

    # поиск кнопок/диалогов по всем фреймам и shadow roots
    result = await page.evaluate("""
      () => {
        const out = {dialogs:[], buttons:[], texts:[]};
        const scan = (root) => {
          // shadow roots
          root.querySelectorAll('*').forEach(el => {
            if (el.shadowRoot) scan(el.shadowRoot);
          });
          // элементы-диалоги
          root.querySelectorAll('paper-dialog, dialog, mwc-dialog, [role=dialog], .goog-modal-dialog, iron-overlay-backdrop')
            .forEach(d => { if(d.offsetParent!==null) out.dialogs.push((d.innerText||'').slice(0,150)); });
          // кнопки
          root.querySelectorAll('button, mwc-button, paper-button, [role=button], .goog-flat-button')
            .forEach(b => { const t=(b.innerText||'').trim(); if(t && t.length<40) out.buttons.push(t); });
        };
        scan(document);
        // фреймы
        document.querySelectorAll('iframe').forEach(f => {
          try { if(f.contentDocument) scan(f.contentDocument); } catch(e){}
        });
        out.buttons = [...new Set(out.buttons)];
        return out;
      }
    """)
    print(json.dumps(result, ensure_ascii=False, indent=2)[:2000])
    await p.stop()

asyncio.run(main())
