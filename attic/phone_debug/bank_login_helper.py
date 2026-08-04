#!/usr/bin/env python3
"""
AIOS Bank Login Helper — автоввод SMS-кода при входе в банк.

Использование:
  python bank_login_helper.py privat [--login_text "номер карты"]
  python bank_login_helper.py privat_biz
  python bank_login_helper.py abank_biz [--login_text "телефон"] [--password "пароль"]

Флоу:
  1. Открывает страницу входа банка в твоём Chrome (через CDP).
  2. Ждёт, пока ты введешь логин/карту и нажмёшь «Вход» (или вводит login_text сам).
  3. Ловит SMS-код из Google Messages и вводит его АВТОМАТИЧЕСКИ.
  4. По завершении — проверяет, что вход прошёл.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time

sys.path.insert(0, "/root/AIOS")


def _bank_class(bank: str):
    from aios_core.platforms.abank_business_chrome_twin_adapter import ABankBusinessChromeTwinAdapter
    from aios_core.platforms.privat_chrome_twin_adapter import PrivatChromeTwinAdapter
    from aios_core.platforms.privat_business_chrome_twin_adapter import PrivatBusinessChromeTwinAdapter
    return {
        "privat": PrivatChromeTwinAdapter,
        "privat_biz": PrivatBusinessChromeTwinAdapter,
        "abank_biz": ABankBusinessChromeTwinAdapter,
    }.get(bank)


async def run(bank: str, login_text: str, password: str):
    cls = _bank_class(bank)
    if cls is None:
        print(f"Неизвестный банк: {bank}")
        return 1
    a = cls()
    print(f"=== {a.bank_name}: открываю страницу входа ===")
    page = await a._ensure_browser()
    await page.goto(a.login_url, wait_until="domcontentloaded", timeout=45000)
    await page.wait_for_timeout(5000)

    # если уже залогинен
    try:
        if await a.is_logged_in(page):
            print("✅ Уже авторизован, вход не нужен.")
            return 0
    except Exception:
        pass

    # ввести логин, если передан
    if login_text:
        try:
            box = page.locator(a.login_field_selector).first
            if await box.count():
                await box.click(timeout=4000)
                await box.fill(login_text)
                await a._click_submit(page)
                await page.wait_for_timeout(2000)
                print("Логин введён")
        except Exception as e:
            print(f"  (автоввод логина: {str(e)[:80]})")

    if password and a.needs_password:
        try:
            box = page.locator(a.password_field_selector).first
            if await box.count():
                await box.click(timeout=4000)
                await box.fill(password)
                await a._click_submit(page)
                await page.wait_for_timeout(2000)
                print("Пароль введён")
        except Exception as e:
            print(f"  (автоввод пароля: {str(e)[:80]})")

    # Ожидание SMS-кода: опрашиваем Google Messages каждые 3 сек до 120 сек
    print("⏳ Жду SMS-код (введите логин/карту и нажмите «Вход», если не введено)...")
    deadline = time.time() + 120
    entered = False
    while time.time() < deadline:
        await page.wait_for_timeout(3000)
        try:
            if await a.is_logged_in(page):
                print("✅ Вход прошёл (кабинет открыт).")
                return 0
        except Exception:
            pass
        code = await a._read_sms_code()
        if code:
            print(f"📩 SMS-код: {code}")
            # ввести код
            filled = False
            for sel in [a.code_field_selector]:
                try:
                    box = page.locator(sel).first
                    if await box.count() and await box.is_visible():
                        await box.click(timeout=2500)
                        await box.fill(code)
                        await box.press("Enter")
                        filled = True
                        break
                except Exception:
                    continue
            if not filled:
                # по цифрам
                digits = [c for c in code if c.isdigit()]
                inputs = page.locator("input[type='tel'], input[type='text'], input:not([type])")
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
            entered = True
            await page.wait_for_timeout(6000)
            break
    if not entered and not await a.is_logged_in(page):
        print("⚠️ SMS-код не получен за 120с. Введите код вручную в браузере.")
    # финальная проверка
    await page.wait_for_timeout(5000)
    try:
        if await a.is_logged_in(page):
            print("✅ Вход подтверждён.")
            return 0
    except Exception:
        pass
    print("Вход завершён (проверьте вкладку).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("bank", choices=["privat", "privat_biz", "abank_biz"])
    ap.add_argument("--login_text", default="")
    ap.add_argument("--password", default="")
    args = ap.parse_args()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        code = loop.run_until_complete(run(args.bank, args.login_text, args.password))
        sys.stdout.flush()
        return code
    except Exception as e:
        print("ERR:", str(e)[:150])
        sys.stdout.flush()
        return 1
    finally:
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception:
            pass
        loop.close()


if __name__ == "__main__":
    sys.exit(main())
