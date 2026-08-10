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

    clicked = False
    # ищем кнопку по всем фреймам (включая cross-origin, доступные через playwright)
    for fr in page.frames:
        try:
            # ищем кнопки с текстом
            loc = fr.locator("button, mwc-button, paper-button, [role=button]").filter(
                has_text="запуст").first
            if await loc.is_visible(timeout=500):
                await loc.click(timeout=2000)
                print(f"👍 Клик в фрейме {fr.url[:40]}: кнопка с 'запуст'")
                clicked = True
                break
        except Exception:
            continue

    if not clicked:
        # пробуем по украинскому/русскому/английскому
        for txt in ["Усе одно запустити", "Усе одно", "Все равно запустить", "Всё равно запустить", "Run anyway", "Запустить", "Выполнить"]:
            try:
                el = page.get_by_text(txt, exact=False).first
                if await el.is_visible(timeout=500):
                    # кликаем по ближайшей кнопке/родителю
                    btn = el.locator("xpath=ancestor::button[1] | xpath=ancestor::mwc-button[1] | xpath=ancestor::*[@role='button'][1] | self::*")
                    try:
                        await btn.first.click(timeout=2000)
                    except Exception:
                        await el.click(timeout=2000)
                    print(f"👍 Клик по тексту '{txt}'")
                    clicked = True
                    break
            except Exception:
                continue

    print("Результат клика:", clicked)
    await asyncio.sleep(8)
    await p.stop()

asyncio.run(main())
