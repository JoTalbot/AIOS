from __future__ import annotations

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
