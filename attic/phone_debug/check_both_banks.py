import asyncio
import sys


async def probe(cls, label, url):
    a = cls()
    try:
        page = await a._ensure_browser()
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(9000)
        print(f"=== {label} ===")
        print("URL:", page.url)
        try:
            logged = await a.is_logged_in(page)
            print("is_logged_in:", logged)
        except Exception as e:
            print("li err:", str(e)[:60])
        body = (await page.inner_text("body"))[:500]
        print("BODY:", body.replace("\n", " | ")[:450])
        print("BALANCE:", a._extract_balance(body))
    except Exception as e:
        print(f"=== {label} ERR: {str(e)[:120]}")


async def main():
    from aios_core.platforms.privat_chrome_twin_adapter import PrivatChromeTwinAdapter
    from aios_core.platforms.abank_business_chrome_twin_adapter import ABankBusinessChromeTwinAdapter
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    if which in ("privat", "both"):
        await probe(PrivatChromeTwinAdapter, "PRIVAT", "https://next.privat24.ua/")
    if which in ("abank", "both"):
        await probe(ABankBusinessChromeTwinAdapter, "ABANK_BIZ", "https://ab.a-bank.com.ua/")


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
