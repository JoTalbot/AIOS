#!/usr/bin/env python3
import sys, asyncio
from playwright.async_api import async_playwright

JS = """
() => {
  const res = {cells: []};
  const cells = document.querySelectorAll('div.cell');
  cells.forEach((c, i) => {
    const n = c.querySelector('.input_area .n, .prompt .n, .cellExecutionLabel, .execution-count');
    const code = c.querySelector('.input_area .CodeMirror, .input_area pre, .view-line');
    let num = '';
    if (n) num = n.innerText.trim();
    else if (code) num = '(no-count)';
    const running = !!c.querySelector('.cell.running, .executing, .pending, .blue, .executing');
    const text = code ? code.innerText.slice(0,40).replace(/\\n/g,' ') : '';
    res.cells.push({idx:i, num:num, running:running, text:text});
  });
  // runtime indicator in toolbar
  const top = document.body.innerText;
  res.hasConnect = /Подключиться|Connect|Підключ/.test(top);
  res.hasRuntime = /runtime|середовище|середовищ|Connected|підключ/.test(top);
  res.menu = top.slice(0, 60);
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
        print("вкладка не найдена"); await p.stop(); return
    import json
    res = await page.evaluate(JS)
    print(json.dumps(res, ensure_ascii=False, indent=2)[:3000])
    await p.stop()

asyncio.run(main())
