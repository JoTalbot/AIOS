"""
Prom.ua Chrome Twin Adapter — использует залогиненную сессию Prom
в Chrome-профиле data/chrome_twin/default/ (вход через VNC).

Функции (read-only):
- check_login — залогинен ли в Prom
- account_info — название магазина, количество товаров/заказов
- products(limit) — последние товары

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


class PromChromeTwinAdapter(ChromeTwinAdapter):
    """Prom.ua через Chrome Twin профиль с уже залогиненной сессией."""

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
        self.is_logged_in = False

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

    async def check_login(self) -> Dict[str, Any]:
        page = await self._ensure_browser()
        await self._goto(page, "https://my.prom.ua/")
        await page.wait_for_timeout(3000)
        url = page.url
        body = ""
        try:
            body = await page.inner_text("body")
        except Exception:
            pass
        logged = "login" not in url.lower() and ("кабінет" in body.lower() or "магазин" in body.lower()
                                                 or "товар" in body.lower() or "заказ" in body.lower())
        self.is_logged_in = logged
        return {"logged_in": logged, "url": url}

    async def account_info(self) -> Dict[str, Any]:
        """Название магазина, количество товаров и заказов."""
        login = await self.check_login()
        if not login.get("logged_in"):
            return {"status": "error", "error": "Prom не залогинен (войдите через VNC)"}
        page = await self._ensure_browser()
        await self._goto(page, "https://my.prom.ua/")
        body = ""
        try:
            body = await page.inner_text("body")
        except Exception:
            pass
        lines = [l.strip() for l in body.splitlines() if l.strip()]
        # название магазина — обычно строка с «магазин»
        shop = None
        for l in lines[:40]:
            low = l.lower()
            if ("магазин" in low or "кабінет" in low) and len(l) < 60 and not l.isdigit():
                shop = l
                break
        products = None
        orders = None
        m = re.search(r"товар[а-я]*\s*[:(]?\s*(\d[\d\s]*)", body, re.IGNORECASE)
        if m:
            products = int(re.sub(r"\D", "", m.group(1)))
        m2 = re.search(r"заказ[а-я]*\s*[:(]?\s*(\d[\d\s]*)", body, re.IGNORECASE)
        if m2:
            orders = int(re.sub(r"\D", "", m2.group(1)))
        shot = f"/tmp/aios_acct_prom_{int(__import__('time').time())}.png"
        try:
            await page.screenshot(path=shot)
        except Exception:
            shot = None
        return {"status": "ok", "shop": shop, "products": products, "orders": orders,
                "screenshot": shot}

    async def products(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Последние товары из кабинета (если страница доступна)."""
        page = await self._ensure_browser()
        await self._goto(page, "https://my.prom.ua/products/")
        await page.wait_for_timeout(4000)
        out = []
        seen = set()
        try:
            texts = await page.eval_on_selector_all(
                "div[data-product-id], [data-testid*='product'], a[href*='/products/']",
                """els => els.map(e => (e.innerText || e.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 120)).filter(t => t.length > 3)""")
            for t in texts or []:
                if t in seen:
                    continue
                seen.add(t)
                out.append({"text": t})
                if len(out) >= limit:
                    break
        except Exception:
            pass
        return out
