#!/usr/bin/env python3
"""Следит за SMS-кодом от банка (A-Bank) и вводит его в открытую вкладку àБізнес."""
import asyncio
import sys
import time

sys.path.insert(0, "/root/AIOS")


async def main():
    from aios_core.platforms.abank_business_chrome_twin_adapter import ABankBusinessChromeTwinAdapter
    a = ABankBusinessChromeTwinAdapter()
    print("[watch] ищу вкладку àБізнес...", flush=True)
    page = await a._ensure_browser()
    pages = [p for p in page.context.pages if "ab.a-bank" in (p.url or "")]
    target = pages[0] if pages else page
    try:
        await target.bring_to_front()
    except Exception:
        pass
    print(f"[watch] вкладка: {target.url}", flush=True)
    deadline = time.time() + 180
    seen = set()
    while time.time() < deadline:
        await asyncio.sleep(3)
        try:
            if await a.is_logged_in(target):
                print("[watch] ✅ вход прошёл", flush=True)
                return
        except Exception:
            pass
        code = await a._read_sms_code()
        if code and code not in seen:
            seen.add(code)
            print(f"[watch] 📩 SMS-код: {code}", flush=True)
            filled = False
            for sel in [a.code_field_selector]:
                try:
                    box = target.locator(sel).first
                    if await box.count() and await box.is_visible():
                        await box.click(timeout=2000)
                        await box.fill(code)
                        await box.press("Enter")
                        filled = True
                        break
                except Exception:
                    continue
            if not filled:
                digits = [c for c in code if c.isdigit()]
                inputs = target.locator("input[type='tel'], input[type='text'], input:not([type])")
                n = await inputs.count()
                done = 0
                for i in range(n):
                    try:
                        box = inputs.nth(i)
                        if not await box.is_visible():
                            continue
                        if done < len(digits):
                            await box.click(timeout=800)
                            await box.fill(digits[done])
                            done += 1
                    except Exception:
                        break
                filled = done >= 3
            if filled:
                print("[watch] код введён", flush=True)
            await asyncio.sleep(6)
    print("[watch] время вышло (180с) — введите код вручную", flush=True)


loop = asyncio.new_event_loop()
try:
    loop.run_until_complete(main())
    sys.stdout.flush()
except Exception as e:
    print("[watch] ERR", str(e)[:120])
    sys.stdout.flush()
finally:
    try:
        loop.run_until_complete(loop.shutdown_asyncgens())
    except Exception:
        pass
    loop.close()
