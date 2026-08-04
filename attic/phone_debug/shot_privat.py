import asyncio


async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        # найти страницу privat24
        pages = [pg for pg in ctx.pages if "privat24" in (pg.url or "")]
        page = pages[0] if pages else await ctx.new_page()
        if not pages:
            await page.goto("https://next.privat24.ua/", wait_until="domcontentloaded", timeout=45000)
        await page.bring_to_front()
        await page.wait_for_timeout(3000)
        await page.screenshot(path="/tmp/privat_state.png", full_page=False)
        print("скриншот: /tmp/privat_state.png")
        print("URL:", page.url)
        # текст, если есть диалог/код
        body = (await page.inner_text("body"))[:600]
        print("BODY:", body.replace("\n", " | ")[:500])


asyncio.run(main())
