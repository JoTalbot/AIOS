import asyncio


async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()
        await page.goto("https://next.privat24.ua/", wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(10000)
        print("URL:", page.url)
        tel = await page.locator("input[type='tel']").count()
        print("tel_inputs(поле карты):", tel)
        body = (await page.inner_text("body"))[:500]
        print("BODY:", body.replace("\n", " | ")[:450])
        has_cab = "Гаманець" in body or "Баланс" in body or "Рахунки" in body or "Сервіси" in body and "Вхід" not in body
        print("КАБИНЕТ?", has_cab)
        await page.screenshot(path="/tmp/privat_now.png")
        await page.close()


asyncio.run(main())
