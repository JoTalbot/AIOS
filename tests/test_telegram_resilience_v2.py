from __future__ import annotations

import socket

from aios_core.autonomy.loop import _looks_like_owner_command
from scripts.telegram_metrics_report import evaluate
from tg_bot.api import TelegramAPI, _telegram_ipv4_family


def test_plain_chat_bypasses_autonomy_planner():
    assert not _looks_like_owner_command("Привет, как дела?")
    assert not _looks_like_owner_command("Расскажи что-нибудь интересное")
    assert not _looks_like_owner_command("Какая ты модель?")


def test_business_commands_use_autonomy_planner():
    assert _looks_like_owner_command("Создай ТТН для отправки")
    assert _looks_like_owner_command("Покажи остатки на складе")
    assert _looks_like_owner_command("Запиши расход 500 гривен")


def test_telegram_json_client_is_ipv4_only():
    assert _telegram_ipv4_family() == socket.AF_INET


def test_non_invasive_telegram_canary_uses_get_me(monkeypatch):
    api = TelegramAPI("test-token")
    monkeypatch.setattr(api, "_request", lambda method, data=None: {"ok": method == "getMe"})
    assert api.get_me() == {"ok": True}


def test_metrics_alert_requires_minimum_sample():
    assert evaluate(
        {
            "events": 2,
            "success_rate": 0,
            "latency": {"send_p95": 99},
            "providers": {"groq": 2},
        }
    ) == []


def test_metrics_detect_send_and_provider_degradation(monkeypatch):
    monkeypatch.setenv("TELEGRAM_MAX_SEND_P95", "5")
    monkeypatch.setenv("TELEGRAM_MIN_COLAB_SHARE", "0.8")
    reasons = evaluate(
        {
            "events": 10,
            "success_rate": 1,
            "latency": {"send_p95": 6},
            "providers": {"colab": 5, "groq": 5},
        }
    )
    assert reasons == ["send_p95", "colab_share"]


def test_polling_errors_are_redacted_and_sigterm_interrupts_blocking_work():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "run_telegram_bot.py").read_text(
        encoding="utf-8"
    )
    assert 're.sub(r"bot[0-9]+:[A-Za-z0-9_-]+", "bot[redacted]"' in source
    assert "raise KeyboardInterrupt" in source
    assert "Ошибка polling: {_redact_runtime_error(exc)}" in source
