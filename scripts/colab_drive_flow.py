#!/usr/bin/env python3
"""Полный авто-flow: копия на Drive → запуск → mount → перенос моделей."""
import sys, asyncio, time
from playwright.async_api import async_playwright

NB="https://colab.research.google.com/github/JoTalbot/AIOS/blob/main/docs/AIOS_Colab_Quant_ML_Training.ipynb"
CDP="http://localhost:9222"

JS_CONFIRM = r"""
() => {
  const EXACT=["Усе одно запустити","Усе одно запустить","Всё равно запустить","Все равно запустить","Run anyway"];
  const L=EXACT.map(function(s){return s.toLowerCase();});
  let hit=null;
  const walk=function(root){
    root.querySelectorAll("*").forEach(function(el){
      if(hit) return;
      if(el.shadowRoot) walk(el.shadowRoot);
      const t=(el.innerText||el.textContent||"").trim();
      if(L.indexOf(t.toLowerCase())>=0){ el.click(); hit=t; }
    });
  };
  walk(document);
  document.querySelectorAll("iframe").forEach(function(f){
    if(hit) return;
    try{ if(f.contentDocument) walk(f.contentDocument);}catch(e){}
  });
  return hit;
}
"""

DRIVE_COPY = r"""
import os, shutil
from google.colab import drive
drive.mount('/content/drive')
src='/content/models'
dst='/content/drive/MyDrive/AIOS_colab_models'
os.makedirs(dst, exist_ok=True)
if os.path.isdir(src):
    for f in os.listdir(src):
        shutil.copy2(os.path.join(src,f), os.path.join(dst,f))
print('DRIVE_COPY_DONE', sorted(os.listdir(dst)) if os.path.isdir(dst) else 'NO_DST')
"""

async def run_cell(page, code):
    await page.bring_to_front()
    await page.mouse.click(500,400)
    await asyncio.sleep(1)
    await page.keyboard.press("Control+m"); await page.keyboard.press("b")
    await asyncio.sleep(1)
    await page.keyboard.type(code, delay=1)
    await asyncio.sleep(1)
    await page.keyboard.press("Shift+Enter")
    await asyncio.sleep(4)

async def confirm(page):
    try:
        hit=await page.evaluate(JS_CONFIRM)
        if hit: print("Подтверждено:", hit); await asyncio.sleep(2)
    except Exception as e:
        print("confirm err", e)

async def main():
    p=await async_playwright().start()
    b=await p.chromium.connect_over_cdp(CDP)
    ctx=b.contexts[0]
    page=None
    for pg in ctx.pages:
        if "Quant_ML_Training" in pg.url: page=pg; break
    if not page:
        print("вкладки нет - открываю")
        page=await ctx.new_page()
        await page.set_viewport_size({"width":1400,"height":900})
        await page.goto(NB, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(8)
    await page.bring_to_front()

    # 1. Попытка "Копировать на Drive" (если есть)
    for label in ["Копіювати на Диск","Копировать на Диск","Copy to Drive","Копіювати на Disk"]:
        try:
            el=page.get_by_text(label, exact=True).first
            if await el.is_visible(timeout=1500):
                await el.click(timeout=3000)
                print("Копирование на Drive:", label)
                await asyncio.sleep(10)
                break
        except Exception:
            continue

    # 2. Подтвердить и запустить все ячейки
    await confirm(page)
    await page.keyboard.press("Control+F9")
    print("Ctrl+F9 отправлен")
    await asyncio.sleep(3)
    await confirm(page)

    # 3. Ждём завершения обучения (~5-7 мин на CPU), затем mount+copy
    # Ждать будем ниже в цикле; здесь запускаем только инициализацию
    print("Обучение запущено. Будем ожидать...")
    await p.stop()

asyncio.run(main())
