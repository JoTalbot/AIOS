"""PrivatBank Бізнес (Приват24 для бізнесу) Chrome Twin Adapter.

«Приват24 для бізнесу» входит через ту же платформу, что и физ-версия:
https://next.privat24.ua (там после входа выбирается роль ФОП/юрлицо).
Проверено вживую 2026-08-03:
  * поле входа — input[type='tel'] (номер карты/телефон), кнопка «Вхід».
  * бизнес-роль переключается после входа (в меню «Бізнес»).
Бизнес требует усиленной аутентификации (КЕП/SMS/push для подписи платежей).

Вход: номер карты + SMS-2FA. Переводы/платежи — только с подтверждения владельца.
"""
from __future__ import annotations

from typing import Any

from .privat_chrome_twin_adapter import PrivatChromeTwinAdapter


class PrivatBusinessChromeTwinAdapter(PrivatChromeTwinAdapter):
    bank_name = "privat_biz"
    # та же платформа, что и физ-версия
    login_url = "https://www.privat24.ua/"
    home_url = "https://next.privat24.ua/"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        if config:
            self.login_url = config.get("login_url", self.login_url)
            self.home_url = config.get("home_url", self.home_url)
            self.sms_sender_hint = config.get("sms_sender_hint", self.sms_sender_hint)
