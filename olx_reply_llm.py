import asyncio
import sys

TEXT = "Добрий день, Дмитро! Відправлення оформлено. Накладна Нової Пошти № 20451502718405. Фара BMW X5 буде відправлена з відділення №8, Кропивницький на Ваше відділення №3 в Олександрії. Відстежуйте за номером накладної. Дякуємо за покупку!"

async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = b.contexts[0] if b.contexts else await b.new_context()
        pg = None
        for x in ctx.pages:
            if "olx" in (x.url or ""):
                pg = x
                break
        if not pg:
            pg = await ctx.new_page()
        await pg.goto("https://www.olx.ua/uk/myaccount/answers/", wait_until="domcontentloaded", timeout=45000)
        await pg.wait_for_timeout(7000)
        clicked = False
        for _ in range(6):
            await pg.wait_for_timeout(2500)
            try:
                item = pg.locator("[data-testid='list-item-user-name']:has-text('[PRIVATE_CONTACT]')").first
                if await item.count():
                    await item.click(timeout=5000)
                    clicked = True
                    break
            except Exception:
                continue
        print("клик по Мише:", clicked)
        await pg.wait_for_timeout(6000)
        filled = False
        for sel in ("textarea[placeholder*='Напишіть']", "textarea[placeholder*='Напишите']", "textarea"):
            try:
                box = pg.locator(sel).first
                if await box.count() and await box.is_visible():
                    await box.click(timeout=3000)
                    await box.fill(TEXT)
                    filled = True
                    break
            except Exception:
                continue
        print("поле заполнено:", filled)
        await pg.wait_for_timeout(800)
        sent = False
        for sel in ("button[aria-label='Submit message']", "button[aria-label*='Надіслати']", "[data-testid*='send']"):
            try:
                bbtn = pg.locator(sel).first
                if await bbtn.count():
                    await bbtn.click(timeout=3000)
                    sent = True
                    break
            except Exception:
                continue
        if not sent:
            try:
                await pg.keyboard.press("Enter")
                sent = True
            except Exception:
                pass
        print("отправлено:", sent)
        await pg.wait_for_timeout(2000)

loop = asyncio.new_event_loop()
try:
    loop.run_until_complete(main())
    sys.stdout.flush()
except Exception as e:
    print("ERR:", str(e)[:150])
    sys.stdout.flush()
finally:
    try:
        loop.run_until_complete(loop.shutdown_asyncgens())
    except Exception:
        pass
    loop.close()
