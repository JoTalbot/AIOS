import asyncio
import sys

TEXT = "Для мене як продавця при поверненні через OLX-доставку немає втрат: OLX повертає товар мені, а гроші повертаються покупцю. Я лише витрачу час на повторну відправку. Тому я чесно описую стан і колір деталі, надсилаю фото до покупки, щоб уникнути таких ситуацій. Тож можете бути спокійні — домовимося про доставку, і якщо щось не так — повернете."


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
        await pg.wait_for_timeout(6000)
        # кликнуть Мишу
        await pg.locator("[data-testid='list-item-user-name']:has-text('[PRIVATE_CONTACT]')").first.click(timeout=8000)
        await pg.wait_for_timeout(5000)
        # найти поле ввода и отправить
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
        # нажать кнопку отправки
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
