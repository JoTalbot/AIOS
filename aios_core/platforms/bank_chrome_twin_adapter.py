"""Bank Chrome Twin Adapter — базовый адаптер украинских банков.

Работает через Chrome Twin (твой залогиненный Chrome по CDP / Playwright),
как и остальные платформы. Ключевые принципы безопасности:
  * Логин — по SMS-2FA: код читается из Google Messages адаптера (find_code),
    ПАРОЛЬ НИГДЕ НЕ ХРАНИТСЯ в коде/конфиге (берётся из Chrome Password Manager
    или вводится тобой вручную при первой авторизации).
  * Чтение (баланс/операции) — безопасно.
  * Переводы/платежи — ТОЛЬКО с явного подтверждения владельца (guardrails MANUAL).

Селекторы сайтов (a-bank.ua, privat24) могут меняться — задаются в конфиге
адаптера/дескриптора. Реальную вёрстку нужно один раз сверить вживую.
"""
from __future__ import annotations

import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .chrome_twin_adapter import ChromeTwinAdapter

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class BankChromeTwinAdapter(ChromeTwinAdapter):
    """Базовый адаптер интернет-банка (SMS-2FA, баланс, операции, перевод)."""

    # Заполняются в подклассах
    bank_name = "bank"
    login_url = ""
    home_url = ""
    sms_sender_hint = ""
    login_field_selector = "input[name*='login'], input[name*='phone'], input[type='tel'], input[type='text']"
    password_field_selector = "input[type='password'], input[name*='pass']"
    code_field_selector = "input[name*='code'], input[name*='otp'], input[placeholder*='код']"
    submit_button_selector = ("button:has-text('Вхід')", "button:has-text('Далі')",
                              "button:has-text('Продовжити')", "button[type='submit']",
                              "button:has-text('Увійти')", "button:has-text('Увійти в систему')")
    balance_selectors: list[str] = []
    txn_row_selector = ""
    # Бизнес-вход часто требует пароль после телефона.
    needs_password = False
    # Текст логина для подсказки, если не передан.
    login_prompt_text = "логин"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config or {})
        self.bank_name = (config or {}).get("bank_name", self.bank_name)
        self.login_url = (config or {}).get("login_url", self.login_url)
        self.home_url = (config or {}).get("home_url", self.home_url)
        self.sms_sender_hint = (config or {}).get("sms_sender_hint", self.sms_sender_hint)
        self.balance_selectors = (config or {}).get("balance_selectors", self.balance_selectors)

    # ------------------------------------------------------------------
    async def _read_sms_code(self) -> Optional[str]:
        """Прочитать последний SMS-код (через Google Messages адаптер)."""
        try:
            from aios_core.platforms.messages_web_chrome_twin_adapter import MessagesWebChromeTwinAdapter
            m = MessagesWebChromeTwinAdapter()
            res = await m.find_code(self.sms_sender_hint)
            if res.get("status") == "ok" and res.get("code"):
                return str(res["code"]).strip()
        except Exception as e:
            print(f"  [BANK:{self.bank_name}] SMS-code error: {str(e)[:120]}")
        return None

    async def is_logged_in(self, page) -> bool:
        """Признак того, что мы уже в кабинете (не на странице входа).

        Более надёжно: URL с login/auth/signin => не залогинен.
        Наличие видимого поля входа (тел/карта) => не залогинен.
        Иначе считаем залогиненным (fallback).
        """
        url = (page.url or "").lower()
        if any(k in url for k in ("login", "auth", "signin", "/auth", "authorization")):
            return False
        # Приват24/банки: наличие видимого поля входа = ещё не залогинен.
        try:
            login_input = page.locator(self.login_field_selector).first
            if await login_input.count() and await login_input.is_visible():
                return False
        except Exception:
            pass
        # Поле ввода кода/пароля тоже может быть признаком незавершённого входа
        try:
            code_input = page.locator(self.code_field_selector).first
            if await code_input.count() and await code_input.is_visible():
                return False
        except Exception:
            pass
        return True

    async def _click_submit(self, page) -> bool:
        """Нажать кнопку продолжения/входа."""
        for sel_btn in self.submit_button_selector:
            try:
                b = page.locator(sel_btn).first
                if await b.count():
                    await b.click(timeout=2500)
                    return True
            except Exception:
                continue
        return False

    async def login(self, login_text: str = "", password: str = "",
                    wait_code_sec: int = 25) -> dict:
        """Войти в интернет-банк: логин (+пароль для бизнеса), SMS-код."""
        page = await self._ensure_browser()
        try:
            if self.login_url:
                await page.goto(self.login_url, wait_until="domcontentloaded", timeout=45000)
                await page.wait_for_timeout(4000)
            # если уже в кабинете — не логинимся
            if await self.is_logged_in(page):
                return {"status": "ok", "message": f"{self.bank_name}: уже авторизован",
                        "url": page.url}
            # поле логина
            filled = False
            for sel in [self.login_field_selector]:
                try:
                    box = page.locator(sel).first
                    if await box.count():
                        await box.click(timeout=4000)
                        if login_text:
                            await box.fill(login_text)
                        filled = True
                        break
                except Exception:
                    continue
            if not filled:
                return {"status": "need_manual",
                        "message": f"{self.bank_name}: войдите вручную в открытом браузере и подтвердите"}
            await self._click_submit(page)
            await page.wait_for_timeout(2500)
            # пароль (для бизнес-входа, если требуется)
            if self.needs_password and password:
                for sel in [self.password_field_selector]:
                    try:
                        box = page.locator(sel).first
                        if await box.count():
                            await box.click(timeout=3000)
                            await box.fill(password)
                            break
                    except Exception:
                        continue
                await self._click_submit(page)
                await page.wait_for_timeout(2500)
            # ждём SMS и вводим код
            code = await self._read_sms_code()
            if not code:
                # пробуем ещё раз после ожидания
                await page.wait_for_timeout(wait_code_sec * 1000)
                code = await self._read_sms_code()
            if code:
                # Приват24/бизнес-банки вводят код по цифрам в отдельные поля.
                # Сначала пробуем одно поле, потом по цифрам.
                filled_code = False
                for sel in [self.code_field_selector]:
                    try:
                        box = page.locator(sel).first
                        if await box.count() and await box.is_visible():
                            await box.click(timeout=2500)
                            await box.fill(code)
                            await box.press("Enter")
                            filled_code = True
                            break
                    except Exception:
                        continue
                if not filled_code:
                    # по цифрам: ищем видимые input в зоне кода
                    digits = [c for c in code if c.isdigit()]
                    inputs = page.locator("input[type='tel'], input[type='text'], input:not([type])")
                    n = await inputs.count()
                    filled_cells = 0
                    for i in range(n):
                        try:
                            box = inputs.nth(i)
                            if not await box.is_visible():
                                continue
                            if filled_cells < len(digits):
                                await box.click(timeout=1000)
                                await box.fill(digits[filled_cells])
                                filled_cells += 1
                        except Exception:
                            break
                    if filled_cells >= 3:
                        filled_code = True
                        await page.wait_for_timeout(2000)
                if not filled_code:
                    return {"status": "need_code",
                            "message": f"{self.bank_name}: не нашёл поле кода, введите {code} вручную"}
                await page.wait_for_timeout(5000)
                return {"status": "ok", "message": f"{self.bank_name}: код введён",
                        "url": page.url}
            return {"status": "need_code",
                    "message": f"{self.bank_name}: не получил SMS-код, введите вручную"}
        except Exception as e:
            return {"status": "error", "error": str(e)[:200]}

    async def get_balance(self) -> dict:
        """Считать баланс с главной страницы кабинета."""
        page = await self._ensure_browser()
        try:
            if self.home_url and self.home_url not in (page.url or ""):
                await page.goto(self.home_url, wait_until="domcontentloaded", timeout=45000)
                await page.wait_for_timeout(5000)
            if not await self.is_logged_in(page):
                return {"status": "need_login", "message": f"{self.bank_name}: нужен вход",
                        "url": page.url}
            # ищем баланс по селекторам + regex «12 345,67 грн»
            text = await page.inner_text("body")
            balance = self._extract_balance(text)
            return {"status": "ok", "bank": self.bank_name, "balance": balance,
                    "url": page.url}
        except Exception as e:
            return {"status": "error", "error": str(e)[:200]}

    @staticmethod
    def _extract_balance(text: str) -> Optional[str]:
        """Найти сумму в гривнах в тексте страницы."""
        if not text:
            return None
        # «1 234,56» грн / uah / ₴
        m = re.search(r"([\d\s\u00a0]+[.,]\d{2})\s*(?:грн|грн\.|₴|uah)", text)
        if m:
            return m.group(1).strip().replace("\u00a0", " ").replace(" ", "")
        # «₴ 1 234»
        m2 = re.search(r"(?:₴|грн)\s*([\d\s\u00a0]+[.,]?\d*)", text)
        if m2:
            return m2.group(1).strip().replace("\u00a0", " ").replace(" ", "")
        return None

    async def get_transactions(self, limit: int = 10) -> dict:
        """Считать последние операции (строка таблицы)."""
        page = await self._ensure_browser()
        try:
            if not await self.is_logged_in(page):
                return {"status": "need_login", "message": f"{self.bank_name}: нужен вход"}
            if self.txn_row_selector:
                rows = await page.locator(self.txn_row_selector).count()
                return {"status": "ok", "bank": self.bank_name, "rows_found": rows}
            # fallback: текст страницы
            text = await page.inner_text("body")
            lines = [l.strip() for l in text.splitlines() if l.strip()][:limit]
            return {"status": "ok", "bank": self.bank_name, "page_lines": lines[:limit]}
        except Exception as e:
            return {"status": "error", "error": str(e)[:200]}

    async def transfer(self, recipient: str, amount: float, note: str = "",
                       confirm: bool = False) -> dict:
        """Инициировать перевод. ВАЖНО: реальный перевод — только с confirm=True
        (владелец подтвердил). Без confirm возвращает need_confirm."""
        if not confirm:
            return {"status": "need_confirm", "bank": self.bank_name,
                    "message": f"Перевод {amount} грн для {recipient} требует подтверждения владельца"}
        # здесь — навигация к форме перевода и заполнение (селекторы специфичны)
        # БЕЗОПАСНОСТЬ: не заполняем/не отправляем, пока селекторы не выверены вживую.
        return {"status": "need_manual",
                "message": f"{self.bank_name}: перевод {amount} грн — заполните форму в открытом браузере"}

    async def health_check(self) -> bool:
        try:
            page = await self._ensure_browser()
            return True
        except Exception:
            return False


async def _make(adapter, method: str, *args) -> dict:
    """Хелпер для вызова из run_account_control."""
    try:
        a = adapter()
        try:
            return await getattr(a, method)(*args)
        finally:
            await a.close()
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}
