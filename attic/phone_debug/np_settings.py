import asyncio
import sys


async def main():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        ctx = b.contexts[0] if b.contexts else await b.new_context()
        pg = None
        for x in ctx.pages:
            if "novaposhta" in (x.url or ""):
                pg = x
                break
        if not pg:
            pg = await ctx.new_page()
        await pg.goto("https://new.novaposhta.ua/dashboard/settings", wait_until="domcontentloaded", timeout=45000)
        await pg.wait_for_timeout(7000)
        print("URL:", pg.url)
        body = (await pg.inner_text("body"))[:800]
        print("BODY:", body.replace("\n", " | ")[:750])
        # ссылки/меню настроек
        links = await pg.eval_on_selector_all("a[href]", "(els)=>els.map(e=>({h:e.href,t:(e.innerText||'').trim().slice(0,30)}))")
        setting_links = [l for l in links if any(k in (l['h']+l['t']).lower() for k in ('sender','відправник','kontragent','контрагент','data','my','адрес','address','contact','контакт'))]
        print("LINKS:", setting_links[:15])


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
