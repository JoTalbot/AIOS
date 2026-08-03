"""A-Bank Chrome Twin Adapter — интернет-банк A-Bank (a-bank.ua).

Вход по SMS-2FA (код читается из Google Messages), чтение баланса/операций.
Переводы — только с подтверждения владельца. Селекторы настраиваются через
конфиг (YAML-дескриптор) и должны быть сверены с живой вёрсткой a-bank.ua.
"""
from __future__ import annotations

from typing import Any

from .bank_chrome_twin_adapter import BankChromeTwinAdapter


class ABankChromeTwinAdapter(BankChromeTwinAdapter):
    bank_name = "abank"
    # ABank24 — личный кабинет A-Bank (официальный вход: телефон + пароль + SMS-код)
    login_url = "https://a24m.a-bank.com.ua/"
    home_url = "https://a24m.a-bank.com.ua/"
    sms_sender_hint = "A-Bank"
    balance_selectors = [
        "[class*='balance']",
        "[class*='Balance']",
        "[data-testid*='balance']",
    ]

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        # разрешить переопределение через конфиг
        if config:
            self.login_url = config.get("login_url", self.login_url)
            self.home_url = config.get("home_url", self.home_url)
            self.sms_sender_hint = config.get("sms_sender_hint", self.sms_sender_hint)
            self.balance_selectors = config.get("balance_selectors", self.balance_selectors)
