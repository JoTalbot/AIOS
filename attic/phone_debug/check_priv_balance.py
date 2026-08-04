import asyncio
import sys


async def m():
    from aios_core.platforms.privat_chrome_twin_adapter import PrivatChromeTwinAdapter
    a = PrivatChromeTwinAdapter()
    page = await a._ensure_browser()
    await page.goto(a.home_url, wait_until="domcontentloaded", timeout=45000)
    await page.wait_for_timeout(9000)
    print("URL:", page.url)
    try:
        print("is_logged_in:", await a.is_logged_in(page))
    except Exception as e:
        print("is_logged_in err:", str(e)[:100])
    tel = await page.locator("input[type='tel']").count()
    print("поле карты:", tel)
    body = (await page.inner_text("body"))[:350]
    print("BODY:", body.replace("\n", " | ")[:320])


loop = asyncio.new_event_loop()
try:
    loop.run_until_complete(m())
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
