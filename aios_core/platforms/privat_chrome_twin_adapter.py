"""PrivatBank Chrome Twin Adapter — Приват24 (privat24.privatbank.ua).

Вход по SMS-2FA (код из Google Messages), чтение баланса/операций.
Переводы — только с подтверждения владельца. Селекторы настраиваются через
конфиг и должны быть сверены с живой вёрсткой Приват24.
"""
from __future__ import annotations

from typing import Any

from .bank_chrome_twin_adapter import BankChromeTwinAdapter


class PrivatChromeTwinAdapter(BankChromeTwinAdapter):
    bank_name = "privat"
    # Приват24 редиректит на next.privat24.ua — живой веб-банкинг.
    login_url = "https://www.privat24.ua/"
    home_url = "https://next.privat24.ua/"
    sms_sender_hint = "PrivatBank"
    # Проверено вживую: поле логина — input[type=tel] (номер карты), кнопка «Вхід».
    login_field_selector = "input[type='tel']"
    code_field_selector = "input[name*='code'], input[name*='otp'], input[placeholder*='код']"
    balance_selectors = [
        "[class*='balance']",
        "[class*='Balance']",
        "[data-testid*='balance']",
    ]

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        if config:
            self.login_url = config.get("login_url", self.login_url)
            self.home_url = config.get("home_url", self.home_url)
            self.sms_sender_hint = config.get("sms_sender_hint", self.sms_sender_hint)
            self.balance_selectors = config.get("balance_selectors", self.balance_selectors)
