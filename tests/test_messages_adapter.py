"""Тесты для aios_core/platforms/messages_web_chrome_twin_adapter.py"""
from __future__ import annotations

import pytest

from aios_core.platforms.messages_web_chrome_twin_adapter import MessagesWebChromeTwinAdapter


class TestExtractCode:
    def test_plain_code(self):
        assert MessagesWebChromeTwinAdapter._extract_code("Ваш код: 9714") == "9714"

    def test_code_with_context(self):
        assert MessagesWebChromeTwinAdapter._extract_code(
            "Ваш код: 9714. Не повідомляйте його нікому.") == "9714"

    def test_long_code(self):
        assert MessagesWebChromeTwinAdapter._extract_code("Код: 12345678") == "12345678"

    def test_no_code(self):
        assert MessagesWebChromeTwinAdapter._extract_code("Привет, как дела?") == ""

    def test_empty(self):
        assert MessagesWebChromeTwinAdapter._extract_code("") == ""

    def test_digit_inside_word_not_code(self):
        # 3 цифры и меньше — не код
        assert MessagesWebChromeTwinAdapter._extract_code("арт. 123") == ""


class TestLatestSmsFormatting:
    def test_latest_has_expected_keys(self):
        convs = [{"sender": "NovaPoshta", "preview": "Ваш код: 9714", "time": "вс",
                  "unread": True}]
        items = []
        for c in convs:
            code = MessagesWebChromeTwinAdapter._extract_code(c.get("preview", ""))
            items.append({
                "sender": c.get("sender", "?"),
                "text": c.get("preview", ""),
                "time": c.get("time", ""),
                "unread": c.get("unread", False),
                "code": code,
            })
        assert items[0]["code"] == "9714"
        assert items[0]["sender"] == "NovaPoshta"


class TestConfig:
    def test_default_profile(self):
        a = MessagesWebChromeTwinAdapter(config={"cdp_url": ""})
        assert a.user_data_dir.endswith("data/chrome_twin/default")
        assert a._site_keyword == "messages.google.com"
