from __future__ import annotations

from tg_bot.llm import _run_restricted_command


def test_console_allows_read_only_diagnostics_without_inheriting_secrets(monkeypatch):
    monkeypatch.setenv("AIOS_TELEGRAM_TOKEN", "must-not-leak")
    code, output = _run_restricted_command("uptime")
    assert code == 0
    assert "must-not-leak" not in output


def test_console_rejects_shell_metacharacters_and_secret_reads():
    for command in (
        "env",
        "cat /run/credentials/telegram_token",
        "uptime; env",
        "sh -c uptime",
        "systemctl restart aios-telegram-bot.service",
    ):
        code, output = _run_restricted_command(command)
        assert code == 126
        assert "allowlist" in output
