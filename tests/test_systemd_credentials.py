from __future__ import annotations

from scripts.install_systemd_credentials import _update_env
from tg_bot.credentials import import_runtime_credential, secret_from_env_or_credential


def test_systemd_credential_overrides_legacy_environment(tmp_path, monkeypatch):
    (tmp_path / "telegram_token").write_text("mounted-secret\n", encoding="utf-8")
    monkeypatch.setenv("CREDENTIALS_DIRECTORY", str(tmp_path))
    monkeypatch.setenv("AIOS_TELEGRAM_TOKEN", "legacy-secret")

    assert secret_from_env_or_credential(
        "AIOS_TELEGRAM_TOKEN", credential="telegram_token"
    ) == "mounted-secret"


def test_runtime_credential_populates_legacy_process_env(tmp_path, monkeypatch):
    (tmp_path / "tailscale_auth_key").write_text("ts-secret\n", encoding="utf-8")
    monkeypatch.setenv("CREDENTIALS_DIRECTORY", str(tmp_path))
    monkeypatch.setenv("TAILSCALE_AUTH_KEY", "old")

    assert import_runtime_credential("TAILSCALE_AUTH_KEY", "tailscale_auth_key") == "ts-secret"
    assert __import__("os").environ["TAILSCALE_AUTH_KEY"] == "ts-secret"


def test_canary_env_update_preserves_non_secret_settings(tmp_path):
    path = tmp_path / ".telegram_canary.env"
    path.write_text("TELEGRAM_MIN_SUCCESS_RATE=0.95\n", encoding="utf-8")
    _update_env(path, {"TELEGRAM_CANARY_CHAT_ID": "123"})
    value = path.read_text(encoding="utf-8")
    assert "TELEGRAM_MIN_SUCCESS_RATE=0.95" in value
    assert "TELEGRAM_CANARY_CHAT_ID=123" in value
    assert path.stat().st_mode & 0o777 == 0o600
