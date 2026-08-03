"""A-Bank Бізнес (àБізнес) Chrome Twin Adapter — интернет-банк для ФОП/юрлиц.

Web-вход àБізнес: https://ab.a-bank.com.ua/auth (работает, в отличие от
физ-версии ABank24). Проверено вживую 2026-08-03:
  * поле логина — input[type='text'] с placeholder «Номер телефону»
  * кнопка «Продовжити»; есть также вход по КЕП и QR-коду.
Физ-версия ABank24 для физлиц неактивна (только мобильное приложение).

Вход: телефон + (пароль) + SMS-2FA. Переводы/платежи — только с подтверждения
владельца (guardrails MANUAL).
"""
from __future__ import annotations

from typing import Any

from .bank_chrome_twin_adapter import BankChromeTwinAdapter


class ABankBusinessChromeTwinAdapter(BankChromeTwinAdapter):
    bank_name = "abank_biz"
    # àБізнес (ФОП/юрлица) — веб-вход, реально работает.
    login_url = "https://ab.a-bank.com.ua/auth"
    home_url = "https://ab.a-bank.com.ua/"
    sms_sender_hint = "A-Bank"
    login_field_selector = "input[type='text']"
    # бизнес-вход обычно требует пароль после телефона
    needs_password = True
    submit_button_selector = (
        "button:has-text('Продовжити')", "button:has-text('Далі')",
        "button:has-text('Увійти')", "button[type='submit']", "button:has-text('Вхід')",
    )

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        if config:
            self.login_url = config.get("login_url", self.login_url)
            self.home_url = config.get("home_url", self.home_url)
            self.sms_sender_hint = config.get("sms_sender_hint", self.sms_sender_hint)
            self.needs_password = bool(config.get("needs_password", self.needs_password))
            self.login_field_selector = config.get("login_field_selector", self.login_field_selector)
