import asyncio
import sys


async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = b.contexts[0] if b.contexts else await b.new_context()
        pg = await ctx.new_page()
        await pg.goto("https://new.novaposhta.ua/", wait_until="domcontentloaded", timeout=45000)
        await pg.wait_for_timeout(8000)
        print("URL:", pg.url)
        try:
            print("TITLE:", (await pg.title())[:80])
        except Exception:
            pass
        body = (await pg.inner_text("body"))[:600]
        print("BODY:", body.replace("\n", " | ")[:550])


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
