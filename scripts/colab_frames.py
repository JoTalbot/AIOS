#!/usr/bin/env python3
import sys, asyncio
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

    def walk(frame, depth):
        try:
            print("  "*depth + f"[frame] {frame.url[:80]}")
        except Exception:
            return
        for f in frame.child_frames:
            walk(f, depth+1)

    print("=== URL вкладки:", page.url)
    print("=== Дерево фреймов:")
    walk(page.main_frame, 0)
    print("=== Контент main_frame (первые 600):")
    try:
        txt = await page.main_frame.evaluate("() => document.body ? document.body.innerText.slice(0,600) : 'no body'")
        print(txt)
    except Exception as e:
        print("err", e)
    await p.stop()

asyncio.run(main())
