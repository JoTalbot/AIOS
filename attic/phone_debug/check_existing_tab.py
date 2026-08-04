import asyncio
import sys


async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
        pages = ctx.pages
        print(f"Всего вкладок: {len(pages)}")
        for pg in pages:
            url = pg.url or ""
            try:
                body = (await pg.inner_text("body"))[:200]
            except Exception:
                body = ""
            print("---")
            print("TAB:", (await pg.title())[:30], "|", url[:60])
            print("  body:", body.replace("\n", " | ")[:180])


loop = asyncio.new_event_loop()
try:
    loop.run_until_complete(main())
    sys.stdout.flush()
except Exception as e:
    print("ERR:", str(e)[:120])
    sys.stdout.flush()
finally:
    try:
        loop.run_until_complete(loop.shutdown_asyncgens())
    except Exception:
        pass
    loop.close()
