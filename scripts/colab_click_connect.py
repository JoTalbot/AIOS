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

    # 1. Найти кнопку подключения по тексту
    find = await page.evaluate("""
      () => {
        const out = [];
        document.querySelectorAll('button, mwc-button, .goog-flat-button, [role=button]').forEach(el => {
          const t = (el.innerText||el.textContent||'').trim();
          if (/подключ|connect|підключ|runtime|сред.execution|середовище/i.test(t) && t.length<40) out.push(t);
        });
        return out.slice(0,10);
      }
    """)
    print("Кнопки подключения:", find)

    # 2. Попробовать кликнуть по кнопке/элементу с текстом Подключиться
    clicked = False
    for text in ["Подключиться", "Підключитися", "Підключити", "Connect"]:
        try:
            btn = page.get_by_text(text, exact=False).first
            if await btn.is_visible(timeout=1500):
                await btn.click(timeout=3000)
                print("👍 Клик по:", text)
                clicked = True
                break
        except Exception as e:
            continue

    # 3. Кликнуть чекбокс reCAPTCHA
    try:
        recaptcha_frame = None
        for fr in page.frames:
            if "recaptcha" in fr.url:
                recaptcha_frame = fr
                break
        if recaptcha_frame:
            cb = recaptcha_frame.locator("#recaptcha-anchor")
            if await cb.is_visible(timeout=2000):
                await cb.click()
                print("👍 Клик по reCAPTCHA checkbox")
                clicked = True
    except Exception as e:
        print("recaptcha:", e)

    if not clicked:
        print("Не нашёл кнопок для клика — возможно runtime уже подключается.")
    await asyncio.sleep(8)
    print("Готово. Проверка через 8 сек...")
    await p.stop()

asyncio.run(main())
