import asyncio
import sys


async def m():
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
        await pg.wait_for_timeout(4000)
        await pg.locator("[data-testid='list-item-user-name']:has-text('[PRIVATE_CONTACT]')").first.click(timeout=5000)
        await pg.wait_for_timeout(4000)
        info = await pg.eval_on_selector_all(
            "[data-testid='message']",
            "(els)=>els.slice(-10).map(e=>{const p=e.parentElement;const pc=p?(p.className||''):'';const sent=/1s1hr5l|sent|outgoing/i.test(pc);return {t:(e.textContent||'').trim(), mine:sent}})")
        for i in info:
            who = "МЫ" if i.get("mine") else "КЛИЕНТ"
            print(f"{who}: {i.get('t','')[:100]}")


loop = asyncio.new_event_loop()
try:
    loop.run_until_complete(m())
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
