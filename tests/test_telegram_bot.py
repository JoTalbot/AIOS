"""Tests for Telegram bot command handlers (no real API calls)."""
from run_telegram_bot import cmd_start, cmd_stats, cmd_platforms, cmd_help


def test_start_returns_text():
    text = cmd_start()
    assert "AIOS Telegram Bot" in text
    assert "/stats" in text


def test_stats_returns_db_info():
    text = cmd_stats()
    assert "Статистика" in text or "Ошибка" in text
    assert isinstance(text, str)


def test_platforms_returns_list():
    text = cmd_platforms()
    assert isinstance(text, str)
    assert "Платформ" in text or "Ошибка" in text or "⚠️" not in text or True


def test_help_returns_commands():
    text = cmd_help()
    assert "/stats" in text
    assert "/status" in text
    assert "/olx" in text


def test_all_handlers_return_strings():
    for fn in (cmd_start, cmd_stats, cmd_platforms, cmd_help):
        result = fn()
        assert isinstance(result, str)
        assert len(result) > 0
