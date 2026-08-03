"""A-Bank Chrome Twin Adapter — интернет-банк A-Bank (àbank24).

ВАЖНО (проверено вживую 2026-08-03): веб-кабинет ABank24 больше НЕ доступен
по адресам a24m/a24 — a-bank.com.ua редиректит на маркетинговую страницу
(/services/abank). А-Bank перешёл на мобильное приложение àbank24.
Поэтому авто-чтение баланса через веб-браузер для A-Bank сейчас НЕ работает.
Этот адаптер оставлен как каркас: если A-Bank вернёт веб-вход или появится
отдельный кабинет для бизнеса — подставить актуальный login_url и селекторы.

Вход: телефон + пароль + SMS-2FA (код из Google Messages). Переводы — только
с подтверждения владельца.
"""
from __future__ import annotations

from typing import Any

from .bank_chrome_twin_adapter import BankChromeTwinAdapter


class ABankChromeTwinAdapter(BankChromeTwinAdapter):
    bank_name = "abank"
    # Веб-вход A-Bank неактивен (см. докстринг). Оставляем URL для справки.
    login_url = "https://a-bank.com.ua/services/abank"
    home_url = "https://a-bank.com.ua/services/abank"
    sms_sender_hint = "A-Bank"
    web_available = False

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        if config:
            self.login_url = config.get("login_url", self.login_url)
            self.home_url = config.get("home_url", self.home_url)
            self.sms_sender_hint = config.get("sms_sender_hint", self.sms_sender_hint)
            self.balance_selectors = config.get("balance_selectors", self.balance_selectors)
            self.web_available = bool(config.get("web_available", self.web_available))

    async def get_balance(self) -> dict:
        if not self.web_available:
            return {"status": "unavailable",
                    "message": "A-Bank: веб-кабинет ABank24 неактивен (только мобильное приложение àbank24). "
                               "Веб-чтение баланса недоступно."}
        return await super().get_balance()
