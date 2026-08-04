import asyncio
import sys


async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = await ctx.new_page()
        await page.goto("https://next.privat24.ua/", wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(8000)
        print("URL:", page.url)
        tel = await page.locator("input[type='tel']").count()
        print("tel_inputs:", tel)
        body = (await page.inner_text("body"))[:400]
        print("BODY:", body.replace("\n", " | ")[:350])
        has_cab = "Гаманець" in body or "Баланс" in body or "Картки" in body or "Рахунки" in body
        print("КАБИНЕТ?", has_cab)
        await page.close()


asyncio.run(main())
