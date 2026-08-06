"""Регрессии приоритетного и карточного общего инбокса."""
from __future__ import annotations


def test_mark_all_inbox_intent_beats_direct(monkeypatch):
    import run_telegram_bot as bot

    called = []
    monkeypatch.setattr(bot, "_inbox_mark_read", lambda api, chat_id: called.append(chat_id))
    handled = bot._handle_unified_inbox_intent(
        object(), 777, "Отметить все не прочитанные сообщения в инбоксе прочитанными"
    )
    assert handled is True
    assert called == [777]


def test_inbox_card_format_marks_service_events_as_low_priority():
    import run_telegram_bot as bot

    assert bot._is_service_preview("Голосовий виклик завершився") is True
    cards = bot._format_inbox([
        {"channel": "ig", "title": "Контакт", "preview": "Голосовий виклик завершився",
         "unread": False, "service": True, "date": ""},
        {"channel": "signal", "title": "Рабочий чат", "preview": "Новый вопрос", "unread": True, "date": ""},
    ])
    assert "╭─" in cards
    assert "⚪ Служебное" in cards
    assert "🔴 Новое" in cards
    assert "ЕДИНЫЙ ИНБОКС" in cards


def test_inbox_refresh_uses_saved_filter(monkeypatch):
    import run_telegram_bot as bot

    captured = []
    monkeypatch.setattr(bot, "_send_unified_inbox",
                        lambda api, chat_id, text="", filters=None, **kwargs: captured.append((chat_id, filters, kwargs)))
    bot._last_inbox[778] = [{"channel": "signal"}]
    bot._last_inbox_filters[778] = {"channels": ["signal"]}
    bot._handle_inbox_callback(object(), 778, 1, "inbox_refresh")
    assert captured == [(778, {"channels": ["signal"]}, {"refresh": True})]
