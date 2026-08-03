"""
Messages (Google Messages for Web) Chrome Twin Adapter
=======================================================
Читает и отправляет SMS через messages.google.com/web в профиле
data/chrome_twin/default/ (тот же Chrome-профиль, где залогинены Google и
другие аккаунты). Привязан к телефону: +380959052288 (видны все SIM).

Зачем:
- Все SMS/коды подтверждения приходят на телефон и дублируются в веб-версии.
- Автоматическое чтение кодов подтверждения (OLX, банки и т.п.) — команда find_code.
- Отправка SMS с телефона.

Архитектура:
- Наследует ChromeTwinAdapter (Playwright + persistent Chrome-профиль).
- Если Chrome уже запущен с --remote-debugging-port (VNC-сессия) —
  подключается через CDP к живой вкладке (cdp_url / env AIOS_CHROME_CDP).
- Иначе запускает собственный браузер с тем же профилем (сессия сохраняется в cookies).

Безопасность:
- Коды и SMS читаются только по явной команде пользователя.
- Пароли не хранятся в коде.
"""
from __future__ import annotations

import os
import re
import shutil
from datetime import datetime, timezone
from typing import Any, Dict, List
from pathlib import Path

from .chrome_twin_adapter import ChromeTwinAdapter

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False
    async_playwright = None

MESSAGES_URL = "https://messages.google.com/web/conversations"
AUTH_URL = "https://messages.google.com/web/authentication"


def _find_chrome_binary() -> str | None:
    """Найти системный Chrome/Chromium."""
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


class MessagesWebChromeTwinAdapter(ChromeTwinAdapter):
    """SMS-адаптер через Google Messages for Web."""

    def __init__(self, config: dict[str, Any] | None = None):
        default_config = {
            "profile": "default",
            "user_data_dir": "data/chrome_twin/default",
            "headless": False,
            "slow_mo": 120,
            "site_keyword": "messages.google.com",
        }
        default_config.update(config or {})
        super().__init__(config=default_config)
        self.executable_path = self.config.get("executable_path") or _find_chrome_binary()

    # ------------------------------------------------------------------ helpers

    async def _wait_ready(self, timeout_ms: int = 25000) -> None:
        """Дождаться загрузки списка разговоров."""
        page = self._page
        try:
            await page.wait_for_selector("mws-conversation-list-item", timeout=timeout_ms)
            return
        except Exception:
            pass
        try:
            await page.wait_for_selector("[data-e2e-conversation-name]", timeout=timeout_ms)
            return
        except Exception:
            pass
        # fallback: ждём любой из признаков интерфейса
        for _ in range(int(timeout_ms / 500)):
            try:
                body = await page.inner_text("body")
                low = body.lower()
                if ("поиск" in low or "search" in low or "разговоры" in low
                        or "conversations" in low or "сообщений" in low):
                    return
            except Exception:
                pass
            await page.wait_for_timeout(500)

    async def _body_text(self) -> str:
        try:
            return await self._page.inner_text("body")
        except Exception:
            return ""

    @staticmethod
    def _extract_code(text: str) -> str:
        """Извлечь код подтверждения (4-8 цифр) из текста SMS."""
        m = re.search(r"\b(\d{4,8})\b", text or "")
        return m.group(1) if m else ""

    # ------------------------------------------------------------------ public API

    async def open_messages(self):
        """Открыть/подготовить страницу Messages for Web."""
        page = await self._ensure_browser()
        url = (page.url or "")
        if "messages.google.com" not in url:
            await page.goto(MESSAGES_URL, wait_until="domcontentloaded", timeout=40000)
            await page.wait_for_timeout(4000)
        # если попали на страницу входа (не привязан телефон) — вернём ошибку выше
        return page

    async def account_info(self) -> Dict[str, Any]:
        """Проверить, что Messages for Web залогинен и привязан к телефону."""
        try:
            page = await self.open_messages()
            await page.wait_for_timeout(3000)
            url = (page.url or "")
            body = await self._body_text()
            low = body.lower()
            if ("authentication" in url or "qr" in url
                    or "відскануйте" in low or "отсканируйте" in low
                    or "qr code" in low or "scan the" in low
                    or "наведіть камеру" in low):
                return {"status": "not_paired",
                        "error": "Телефон не привязан к Messages for Web. "
                                 "Откройте VNC и отсканируйте QR-код телефоном.",
                        "url": url}
            await self._wait_ready(15000)
            return {"status": "ok", "url": url, "paired": True}
        except Exception as e:
            return {"status": "error", "error": str(e)[:300]}

    async def list_conversations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Список последних SMS-переписок (имя отправителя + превью)."""
        page = await self.open_messages()
        await self._wait_ready()
        try:
            items = await page.eval_on_selector_all(
                "mws-conversation-list-item",
                """(els, limit) => els.slice(0, limit).map(e => {
                    const q = s => (e.querySelector(s) || {}).textContent || '';
                    const link = e.querySelector('a[href*="/web/conversations/"]');
                    return {
                        name: q('[data-e2e-conversation-name]').trim(),
                        preview: q('[data-e2e-conversation-snippet]').trim(),
                        time: q('mws-relative-timestamp').trim(),
                        unread: !!e.querySelector('[data-e2e-is-unread="true"], mws-conversation-list-item-unread-count'),
                        href: (link ? link.getAttribute('href') : '')
                    };
                })""",
                limit)
            return [it for it in items if it.get("name")]
        except Exception:
            # fallback: парсим текст
            body = await self._body_text()
            lines = [l.strip() for l in body.splitlines() if l.strip()]
            return [{"name": l, "preview": ""} for l in lines[:limit]]

    async def read_conversation(self, contact: str, limit: int = 15) -> Dict[str, Any]:
        """Открыть переписку с контактом и вернуть последние сообщения."""
        page = await self.open_messages()
        await self._wait_ready()
        # ищем разговор по имени/номеру
        loc = page.locator(
            f"mws-conversation-list-item:has-text('{contact}')").first
        try:
            await loc.click(timeout=8000)
            await page.wait_for_timeout(2500)
        except Exception:
            return {"status": "error", "error": f"Переписка «{contact}» не найдена"}
        try:
            msgs = await page.eval_on_selector_all(
                "mws-message-wrapper",
                """(els, limit) => els.slice(-limit).map(e => {
                    const t = (e.querySelector('mws-message-part-content') || e).textContent || '';
                    const ts = (e.querySelector('mws-absolute-timestamp, mws-relative-timestamp') || {}).textContent || '';
                    return {text: t.trim(), sender: '', time: ts.trim()};
                })""",
                limit)
        except Exception:
            msgs = []
        if not msgs:
            body = await self._body_text()
            # грубо: текст после открытия
            msgs = [{"text": body[:500], "sender": contact, "time": ""}]
        # возвращаемся к списку
        try:
            back = page.locator("mws-back-button, [aria-label*='Назад'], [aria-label*='Back']").first
            if await back.count():
                await back.click(timeout=3000)
        except Exception:
            pass
        return {"status": "ok", "contact": contact, "messages": msgs[-limit:][::-1]}

    async def latest_sms(self, limit: int = 10) -> Dict[str, Any]:
        """Последние SMS по всем перепискам (по превью, без входа в каждую)."""
        convs = await self.list_conversations(limit)
        items = []
        for c in convs:
            code = self._extract_code(c.get("preview", ""))
            items.append({
                "sender": c.get("name", "?"),
                "text": c.get("preview", ""),
                "time": c.get("time", ""),
                "unread": c.get("unread", False),
                "code": code,
            })
        return {"status": "ok", "sms": items, "count": len(items)}

    async def find_code(self, sender_hint: str = "") -> Dict[str, Any]:
        """Найти последний код подтверждения в SMS.

        Если sender_hint задан (например «OLX», «Приват»), ищем только у него.
        Открывает найденную переписку, чтобы прочитать полный текст сообщения.
        """
        page = await self.open_messages()
        await self._wait_ready()
        convs = await self.list_conversations(20)
        candidates = []
        for c in convs:
            name = (c.get("name") or "").lower()
            if sender_hint and sender_hint.lower() not in name:
                continue
            preview = c.get("preview", "")
            code = self._extract_code(preview)
            candidates.append({"sender": c.get("name", "?"), "preview": preview,
                               "code": code, "time": c.get("time", "")})
        # сначала те, у кого код уже в превью
        with_code = [c for c in candidates if c["code"]]
        if with_code:
            return {"status": "ok", "code": with_code[0]["code"],
                    "sender": with_code[0]["sender"],
                    "message": with_code[0]["preview"],
                    "time": with_code[0]["time"]}
        # иначе — открываем первую подходящую переписку и читаем полностью
        if candidates:
            r = await self.read_conversation(candidates[0]["sender"], limit=5)
            if r.get("status") == "ok":
                for m in r.get("messages", []):
                    code = self._extract_code(m.get("text", ""))
                    if code:
                        return {"status": "ok", "code": code,
                                "sender": candidates[0]["sender"],
                                "message": m.get("text", ""),
                                "time": m.get("time", "")}
        return {"status": "error",
                "error": ("Код не найден" + (f" от «{sender_hint}»" if sender_hint else "")
                          + " в последних SMS")}

    async def send_sms(self, contact: str, text: str) -> Dict[str, Any]:
        """Отправить SMS контакту/номеру через Messages for Web."""
        page = await self.open_messages()
        await self._wait_ready()
        # новая переписка: кнопка «+» / поиск
        clicked = False
        for sel in ("mws-fab", "[aria-label*='Новое сообщение']", "[aria-label*='Start chat']",
                    "[data-e2e-fab]", "mws-start-new-conversation-button"):
            try:
                b = page.locator(sel).first
                if await b.count():
                    await b.click(timeout=3000)
                    clicked = True
                    break
            except Exception:
                continue
        if not clicked:
            # иначе ищем в списке
            try:
                sb = page.locator("mws-search-input, input[placeholder*='Поиск'], input[placeholder*='Search']").first
                if await sb.count():
                    await sb.click(timeout=3000)
            except Exception:
                pass
        await page.wait_for_timeout(1500)
        # ввод контакта/номера
        typed = False
        for sel in ("mws-search-input", "input[placeholder*='Поиск']", "input[placeholder*='Search']",
                    "input[aria-label*='имя или номер']", "input[type='text']"):
            try:
                inp = page.locator(sel).first
                if await inp.count() and await inp.is_visible():
                    await inp.fill(contact)
                    typed = True
                    break
            except Exception:
                continue
        if not typed:
            try:
                await page.keyboard.type(contact, delay=60)
            except Exception:
                pass
        await page.wait_for_timeout(2500)
        # клик по результату
        try:
            res = page.locator("mws-conversation-list-item:has-text('" + contact + "')").first
            await res.click(timeout=5000)
        except Exception:
            # fallback: первая строка в списке контактов
            try:
                first = page.locator("mws-conversation-list-item").first
                if await first.count():
                    await first.click(timeout=3000)
            except Exception:
                pass
        await page.wait_for_timeout(2000)
        # ввод текста в композер
        sent_text = False
        for sel in ("mws-composer", "textarea[aria-label*='Повідомлення']", "textarea[aria-label*='Message']",
                    "[contenteditable='true']"):
            try:
                box = page.locator(sel).first
                if await box.count() and await box.is_visible():
                    await box.click(timeout=3000)
                    await box.fill(text)
                    sent_text = True
                    break
            except Exception:
                continue
        if not sent_text:
            try:
                await page.keyboard.type(text, delay=40)
            except Exception:
                return {"status": "error", "error": "Не удалось ввести текст сообщения"}
        await page.wait_for_timeout(800)
        # отправка
        sent = False
        for sel in ("mws-composer-send-button", "[data-e2e-send-button]",
                    "button[aria-label*='Відправити']", "button[aria-label*='Send']"):
            try:
                b = page.locator(sel).first
                if await b.count():
                    await b.click(timeout=3000)
                    sent = True
                    break
            except Exception:
                continue
        if not sent:
            try:
                await page.keyboard.press("Enter")
                sent = True
            except Exception:
                pass
        await page.wait_for_timeout(1500)
        return {"status": "sent", "to": contact, "text": text[:200]} if sent else \
               {"status": "error", "error": "Не найдена кнопка отправки"}

    async def screenshot(self, path: str = "/tmp/messages_sms.png") -> Dict[str, Any]:
        """Скриншот текущего экрана Messages."""
        try:
            page = await self.open_messages()
            await page.screenshot(path=path)
            return {"status": "ok", "screenshot": path}
        except Exception as e:
            return {"status": "error", "error": str(e)[:300]}


# Alias for backward compat
MessagesWebAdapter = MessagesWebChromeTwinAdapter
