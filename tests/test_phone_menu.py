"""Phone navigation keyboard exposes metadata-safe phone controls."""
from __future__ import annotations


def test_phone_menu_button_mapping_and_rendering():
    import run_telegram_bot as bot

    assert bot.BUTTON_ACTIONS["📲 Телефон"] == "menu_phone"
    assert bot.BUTTON_ACTIONS["📲 Центр телефона"] == "phone_center"
    assert bot.BUTTON_ACTIONS["📤 Экспорт метрик"] == "phone_metrics_export"
    assert bot.BUTTON_ACTIONS["🗄 Здоровье данных"] == "phone_data_health"
    assert bot.BUTTON_ACTIONS["🧪 Сценарии"] == "phone_workflows"

    class API:
        def __init__(self): self.messages = []
        def send_message(self, *args, **kwargs): self.messages.append((args, kwargs))

    api = API()
    bot._handle_button_inner(api, 1, "menu_phone")
    text, kwargs = api.messages[-1]
    assert "Телефон AIOS" in str(text)
    assert kwargs["reply_markup"] == bot.PHONE_MENU_KEYBOARD
