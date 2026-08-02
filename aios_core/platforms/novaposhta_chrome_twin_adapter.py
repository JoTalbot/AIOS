"""
Nova Poshta (Новая Пошта) Chrome Twin Adapter — отслеживание посылок и кабинет
через Chrome-профиль data/chrome_twin/default/ (вход через VNC опционален).

Функции:
- track(ttn) — статус посылки по номеру ТТН (без логина, публичное отслеживание)
- account_info — кабинет: имя, баланс (если залогинен)
- warehouses_search(query) — поиск отделений (публичная страница)

Архитектура:
- Наследует ChromeTwinAdapter (Playwright + persistent Chrome-профиль)
- Системный google-chrome-stable
"""
from __future__ import annotations

import os
import re
import shutil
from typing import Any, Dict, List, Optional
from pathlib import Path

from .chrome_twin_adapter import ChromeTwinAdapter

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    async_playwright = None


def _find_chrome_binary() -> Optional[str]:
    candidates = [
        "/usr/bin/google-chrome-stable",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
        shutil.which("google-chrome-stable"),
        shutil.which("google-chrome"),
        shutil.which("chromium-browser"),
        shutil.which("chromium"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None


class NovaPoshtaChromeTwinAdapter(ChromeTwinAdapter):
    """Новая Пошта через Chrome Twin."""

    def __init__(self, config: dict[str, Any] | None = None):
        default_config = {
            "profile": "default",
            "user_data_dir": "data/chrome_twin/default",
            "headless": False,
            "slow_mo": 120,
        }
        default_config.update(config or {})
        super().__init__(config=default_config)
        self.executable_path = self.config.get("executable_path") or _find_chrome_binary()

    async def _ensure_browser(self):
        if self._page and self._context:
            return self._page
        if not HAS_PLAYWRIGHT:
            raise RuntimeError("Playwright не установлен")
        self._playwright = await async_playwright().start()
        kwargs: dict[str, Any] = dict(
            user_data_dir=str(Path(self.user_data_dir).resolve()),
            headless=self.headless,
            slow_mo=self.slow_mo,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
        )
        if self.executable_path:
            kwargs["executable_path"] = self.executable_path
        self._context = await self._playwright.chromium.launch_persistent_context(**kwargs)
        self._browser = self._context
        self._page = self._context.pages[0] if len(self._context.pages) > 0 else await self._context.new_page()
        try:
            from .chrome_twin_vision import ChromeTwinVision
            self._vision = ChromeTwinVision(self._page)
        except Exception:
            pass
        return self._page

    async def _goto(self, page, url: str, retries: int = 3):
        for i in range(retries):
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                await page.wait_for_timeout(4000)
                return True
            except Exception:
                await page.wait_for_timeout(2500)
        return False

    _STATUS_KEYS = ("отримано", "отримана", "отриманий", "відправлен", "прибуло",
                    "посилка", "доставлено", "в дорозі", "оформлено", "у відділенні",
                    "прибув", "на складі", "видано", "видана", "відмова",
                    "received", "sent", "delivered", "tracking", "creating", "created")

    def _api_url(self, ttn: str) -> str:
        return f"https://api.novapost.com/site/v.1.0/shipments/tracking/{ttn}"

    async def track(self, ttn: str, phone: str = "") -> Dict[str, Any]:
        """Отследить посылку по ТТН через официальный публичный API Новой Пошты."""
        import json as _json
        import urllib.request as _urllib

        ttn = re.sub(r"\D", "", ttn or "")
        if len(ttn) < 8:
            return {"status": "error", "error": "Некорректный номер ТТН"}
        try:
            req = _urllib.Request(self._api_url(ttn), headers={
                "User-Agent": "Mozilla/5.0", "Accept": "application/json"})
            with _urllib.urlopen(req, timeout=30) as r:
                data = _json.loads(r.read())
        except Exception as e:
            return {"status": "error", "error": f"API: {str(e)[:200]}"}

        tracking = data.get("tracking") or []
        if not tracking:
            return {"status": "ok", "ttn": ttn, "found": False,
                    "tracking_status": "Посилку не знайдено (перевірте номер ТТН)"}

        events = []
        for ev in tracking:
            events.append({
                "date": (ev.get("date") or "")[:16],
                "event": ev.get("event_name") or ev.get("event") or "",
                "settlement": ev.get("settlement_name") or "",
                "division": ev.get("division_name") or "",
            })
        last = events[-1] if events else {}
        # статус — последнее событие (на русском/украинском уже в event)
        status = last.get("event") or "не определён"
        details = {
            "sender": data.get("sender", {}).get("settlement"),
            "recipient": data.get("recipient", {}).get("settlement"),
            "scheduled_delivery": (data.get("scheduled_delivery_date") or "")[:16],
            "payer": data.get("payer_type"),
            "weight": data.get("total_weight"),
        }
        return {"status": "ok", "ttn": ttn, "found": True,
                "tracking_status": status,
                "events": events[-6:],
                "details": details}

    async def warehouses_search(self, query: str, limit: int = 8) -> Dict[str, Any]:
        """Поиск отделений Новой Пошты по адресу/городу."""
        page = await self._ensure_browser()
        await self._goto(page, "https://novaposhta.ua/office")
        # поле поиска
        try:
            box = page.locator("input[type='search'], input[placeholder*='Пошук'], input[placeholder*='Поиск'], input[placeholder*='Search']").first
            await box.wait_for(state="visible", timeout=8000)
            await box.fill(query)
            await page.wait_for_timeout(4000)
        except Exception:
            pass
        body = ""
        try:
            body = await page.inner_text("body")
        except Exception:
            pass
        lines = [l.strip() for l in body.splitlines() if l.strip()]
        # отделения — строки с номером отделения
        offices = []
        for l in lines[:60]:
            if re.search(r"(відділенн|отделение|№\s?\d|No\.?\s?\d)", l, re.IGNORECASE) and len(l) > 5:
                offices.append(l[:150])
                if len(offices) >= limit:
                    break
        return {"status": "ok", "query": query, "offices": offices}

    async def account_info(self) -> Dict[str, Any]:
        """Кабинет Новой Пошты (если залогинен)."""
        page = await self._ensure_browser()
        await self._goto(page, "https://new.novaposhta.ua/dashboard/invoices-my")
        await page.wait_for_timeout(8000)
        body = ""
        try:
            body = await page.inner_text("body")
        except Exception:
            pass
        lines = [l.strip() for l in body.splitlines() if l.strip()]
        # страница входа: URL login ИЛИ очень короткий текст (без меню кабинета)
        is_login_page = "login" in page.url.lower() or \
                        ("увійти" in body.lower() and "мої посилки" not in body.lower()) or \
                        (len(lines) < 6 and "увійти" in body.lower())
        if is_login_page:
            return {"status": "error", "error": "Кабинет Новой Пошты не залогинен (войдите через VNC)"}
        # ФИО — строка из 3 слов (заглавные или с большой буквы), без служебных слов
        name = None
        for l in lines:
            if re.search(r"\b[А-ЯІЇЄҐ][А-ЯІЇЄҐа-яіїєґ']+\s+[А-ЯІЇЄҐ][А-ЯІЇЄҐа-яіїєґ']+\s+[А-ЯІЇЄҐ][А-ЯІЇЄҐа-яіїєґ']+", l) \
                    and len(l) < 80 and "пошта" not in l.lower() and "договір" not in l.lower() \
                    and "посилк" not in l.lower() and "накладн" not in l.lower():
                name = l
                break
        balance = None
        m = re.search(r"([\d\s.,]+)\s*грн", body)
        if m:
            balance = m.group(1).strip()
        shot = f"/tmp/aios_acct_np_acc_{int(__import__('time').time())}.png"
        try:
            await page.screenshot(path=shot)
        except Exception:
            shot = None
        return {"status": "ok", "name": name, "balance": balance, "screenshot": shot}
