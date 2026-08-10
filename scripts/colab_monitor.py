#!/usr/bin/env python3
"""
AIOS Colab Monitor - чтение прогресса выполнения ноутбука через CDP 9222.

Запуск:
    python scripts/colab_monitor.py [notebook_key]
"""

from __future__ import annotations

import sys
import asyncio

from playwright.async_api import async_playwright

JS_READ_CELLS = """
() => {
  const cells = document.querySelectorAll('div.cell.code, div.code_cell, div.cell');
  const res = [];
  cells.forEach((c, i) => {
    const out = c.querySelector('div.output_area pre, div.output_subarea, div.output_html');
    const running = c.querySelector('.cell.running, .pending, .executing');
    let text = '';
    if (out) text = out.innerText.slice(0, 250);
    res.push('[' + i + ']' + (running ? ' RUNNING' : '') + ': ' + text.replace(/\\n/g, ' '));
  });
  return res.join('\\n');
}
"""


async def main():
    nb_key = sys.argv[1] if len(sys.argv) > 1 else "AIOS_Colab_Quant_ML_Training"
    p = await async_playwright().start()
    b = await p.chromium.connect_over_cdp("http://localhost:9222")
    ctx = b.contexts[0] if b.contexts else await b.new_context()
    page = None
    for pg in ctx.pages:
        if nb_key in pg.url:
            page = pg
            break
    if not page:
        print("Вкладка не найдена:", nb_key)
        await p.stop()
        return

    title = await page.title()
    out = await page.evaluate(JS_READ_CELLS)
    print("=== Вкладка:", title, "===")
    print(out)
    await p.stop()


if __name__ == "__main__":
    asyncio.run(main())
