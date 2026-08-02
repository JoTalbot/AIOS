#!/usr/bin/env python3
"""
AIOS OLX Boost — поднятие/контроль моих объявлений OLX.
Открывает кабинет, кликает «Оголошення» в меню, ищет кнопку «Підняти/Обновити»
и кликает (по одной). Отчёт: количество объявлений и поднятий.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


async def _boost(do_boost: bool) -> dict:
    from aios_core.platforms.olx_chrome_twin_adapter import OLXChromeTwinAdapter
    a = OLXChromeTwinAdapter(config={"olx_login": "959052288"})
    try:
        page = await a._ensure_browser()
        await page.goto("https://www.olx.ua/uk/myaccount/", wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(6000)
        # клик по пункту «Оголошення» в левом меню
        clicked = False
        for sel in ("text=Оголошення", "a[href*='announcement']", "text=Мои объявления"):
            try:
                el = page.locator(sel).first
                if await el.count():
                    await el.click(force=True, timeout=4000)
                    await page.wait_for_timeout(6000)
                    clicked = True
                    print(f"клик по {sel}, URL:", page.url)
                    break
            except Exception:
                continue
        body = await page.inner_text("body")
        lines = [l.strip() for l in body.splitlines() if l.strip()]
        # объявления: заголовки карточек + кнопки
        ads = []
        refresh_btns = 0
        for l in lines:
            low = l.lower()
            if any(k in low for k in ("підняти", "обновити", "оновити", "поднять", "обновить")):
                refresh_btns += 1
            elif len(l) > 6 and not any(k in low for k in (
                    "профіль", "профиль", "чат", "повідомлення", "мої", "обра", "вийти",
                    "додати оголошення", "платежі", "рейтинг", "налаштування", "доставка",
                    "пошуки", "бізнес", "допомога", "умови", "політика", "реклама",
                    "рахунок", "баланс", "бонус", "мобільні", "сторінку не знайдено",
                    "перейти до основного")):
                ads.append(l[:90])
        result = {"status": "ok", "ads_found": len(ads), "refresh_buttons": refresh_btns,
                  "ads_preview": ads[:8]}
        if do_boost and refresh_btns:
            # кликаем первую кнопку «Підняти» (осторожно — OLX может подтверждать)
            for sel in ("button:has-text('Підняти')", "button:has-text('Обновити')",
                        "button:has-text('Оновити')", "button:has-text('Поднять')",
                        "button:has-text('Обновить')"):
                try:
                    btn = page.locator(sel).first
                    if await btn.count():
                        await btn.click(timeout=4000)
                        await page.wait_for_timeout(4000)
                        result["boosted"] = True
                        print("Поднял первое объявление")
                        break
                except Exception:
                    continue
        await page.screenshot(path="/tmp/olx_boost.png")
        result["screenshot"] = "/tmp/olx_boost.png"
        return result
    finally:
        await a.close()


def main() -> None:
    do_boost = "--boost" in sys.argv
    try:
        r = asyncio.run(_boost(do_boost))
        print(json.dumps(r, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)[:300]}))


if __name__ == "__main__":
    main()
