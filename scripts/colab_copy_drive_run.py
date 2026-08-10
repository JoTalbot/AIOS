#!/usr/bin/env python3
import sys, asyncio, time
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

    # 1. Кнопка "Копировать на Диск"
    for label in ["Копіювати на Диск", "Копировать на Диск", "Copy to Drive"]:
        try:
            btn = page.get_by_text(label, exact=True).first
            if await btn.is_visible(timeout=1500):
                await btn.click(timeout=4000)
                print("👍 Клик по 'Копировать на Диск'")
                await asyncio.sleep(10)  # ждём открытия копии
                break
        except Exception:
            continue

    # 2. После копирования URL меняется на /drive/... — ищем обновлённую вкладку
    #    Попробуем на текущей странице запустить всё
    #    Сначала Ctrl+F9
    await page.keyboard.press("Control+F9")
    print("▶️ Ctrl+F9 (Run all) отправлен")
    await asyncio.sleep(8)

    # 3. Подтверждения
    for selector in ["button:has-text('Run anyway')", "button:has-text('Все равно')",
                     "button:has-text('Всё равно')", "button:has-text('Запустить')",
                     "colab-callout button", "#ok", "mwc-button#ok", "paper-button#ok"]:
        try:
            el = page.locator(selector)
            if await el.is_visible(timeout=1200):
                await el.click()
                print("👍 Подтверждение:", selector)
                break
        except Exception:
            continue

    print("Готово.")
    await p.stop()

asyncio.run(main())
