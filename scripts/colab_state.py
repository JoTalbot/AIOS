#!/usr/bin/env python3
import sys, asyncio
from playwright.async_api import async_playwright

JS = """
() => {
  const res = {};
  // кнопки подключения
  res.connect = !!document.querySelector('#connect, #reconnect');
  // диалоги
  const dialogs = [];
  document.querySelectorAll('paper-dialog, dialog, mwc-dialog, .goog-modal-dialog, colab-dialog')
    .forEach(d => { if (d.offsetParent !== null) dialogs.push(d.innerText.slice(0,200)); });
  res.dialogs = dialogs;
  // текст с кнопками run
  const btns = [];
  document.querySelectorAll('button').forEach(b => {
    const t = (b.innerText||'').trim();
    if (/run|запуск|выполн|connect|подключ/i.test(t)) btns.push(t.slice(0,50));
  });
  res.buttons = btns.slice(0,10);
  // ошибки
  const errs = [];
  document.querySelectorAll('.output_error, .error').forEach(e => { if(e.offsetParent) errs.push(e.innerText.slice(0,150)); });
  res.errors = errs.slice(0,3);
  // клетки занятости
  res.runningCells = document.querySelectorAll('.cell.running, .executing, .pending').length;
  res.connected = document.body.innerText.includes('Connected') || !!document.querySelector('colab-connected-indicator');
  res.bodySample = document.body.innerText.slice(0, 500);
  return res;
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
        print("Вкладка не найдена"); await p.stop(); return
    import json
    res = await page.evaluate(JS)
    print(json.dumps(res, ensure_ascii=False, indent=2)[:2500])
    await p.stop()

asyncio.run(main())
