from __future__ import annotations

from scripts.install_systemd_credentials import _purge_env
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


def test_canary_env_purge_preserves_non_secret_settings(tmp_path):
    path = tmp_path / ".telegram_canary.env"
    path.write_text(
        "TELEGRAM_MIN_SUCCESS_RATE=0.95\n"
        "TELEGRAM_CANARY_CHAT_ID=123\n"
        "TELEGRAM_ALERT_CHAT_ID=123\n",
        encoding="utf-8",
    )
    _purge_env(path)
    value = path.read_text(encoding="utf-8")
    assert "TELEGRAM_MIN_SUCCESS_RATE=0.95" in value
    assert "TELEGRAM_CANARY_CHAT_ID" not in value
    assert "TELEGRAM_ALERT_CHAT_ID" not in value
    assert path.stat().st_mode & 0o777 == 0o600


def test_resilience_units_mount_credentials_and_enable_full_canary():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    canary = (root / "deploy/systemd/aios-telegram-colab-canary.service").read_text()
    metrics = (root / "deploy/systemd/aios-telegram-metrics-report.service").read_text()
    bot = (root / "deploy/systemd/aios-tg.service").read_text()
    assert "User=aios-telegram" in bot
    assert "AIOS_TELEGRAM_STATE_DIR=/var/lib/aios/telegram" in bot
    assert "LoadCredential=telegram_token:" in canary
    assert "LoadCredential=telegram_owner_chat_id:" in canary
    assert "LoadCredential=telegram_queue_key:" in canary
    assert "Environment=CANARY_SEND_TELEGRAM=1" in canary
    assert "LoadCredential=telegram_token:" in metrics
    assert "LoadCredential=telegram_owner_chat_id:" in metrics
    assert "LoadCredential=telegram_queue_key:" in metrics


def test_secondary_colab_chrome_starts_memory_safe():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    dropin = (
        root
        / "deploy/systemd/aios-chrome-colab-secondary.service.d/40-memory-safe-startup.conf"
    ).read_text()
    assert "--restore-last-session" not in dropin
    assert "--renderer-process-limit=4" in dropin
    assert "MemoryMax=1200M" in dropin


def test_queue_cipher_uses_systemd_credential_directory(tmp_path, monkeypatch):
    from cryptography.fernet import Fernet
    from tg_bot.outbox import TelegramOutbox

    credentials = tmp_path / "credentials"
    credentials.mkdir()
    (credentials / "telegram_queue_key").write_bytes(Fernet.generate_key() + b"\n")
    monkeypatch.setenv("CREDENTIALS_DIRECTORY", str(credentials))

    class API:
        pass

    database = tmp_path / "state" / "outbox.sqlite3"
    TelegramOutbox(API(), database)
    assert not database.with_suffix(database.suffix + ".key").exists()


def test_root_only_source_credential_supports_legacy_cron(tmp_path, monkeypatch):
    source = tmp_path / "credentials"
    source.mkdir(mode=0o700)
    token = source / "telegram_token"
    token.write_text("source-secret\n", encoding="utf-8")
    token.chmod(0o600)
    monkeypatch.delenv("CREDENTIALS_DIRECTORY", raising=False)
    monkeypatch.setenv("AIOS_CREDENTIAL_SOURCE_DIR", str(source))

    from tg_bot.credentials import read_systemd_credential

    assert read_systemd_credential("telegram_token") == "source-secret"


def test_legacy_secret_audit_never_returns_values(tmp_path):
    from scripts.audit_legacy_secrets import audit

    env = tmp_path / ".env"
    env.write_text(
        "AIOS_TELEGRAM_TOKEN=super-private\nTELEGRAM_CANARY_CHAT_ID=123\nSAFE=value\n",
        encoding="utf-8",
    )
    findings = audit([env])
    assert findings == [
        {"path": str(env), "key": "AIOS_TELEGRAM_TOKEN"},
        {"path": str(env), "key": "TELEGRAM_CANARY_CHAT_ID"},
    ]
    assert "super-private" not in str(findings)
    assert "123" not in str(findings)


def test_installer_enables_snapshot_backup_drill_and_alert_canary():
    from pathlib import Path

    script = (
        Path(__file__).resolve().parents[1]
        / "scripts/install_telegram_resilience_units.sh"
    ).read_text(encoding="utf-8")
    assert "--purge-managed-env" in script
    assert "aios-telegram-metrics-snapshot.service" in script
    assert "aios-telegram-queue-backup.timer" in script
    assert "aios-telegram-queue-restore-drill.timer" in script
    assert "aios-telegram-offsite-backup.timer" in script
    assert "aios-docker-runtime-credentials.service" in script
    assert "aios-alertmanager-delivery-canary.timer" in script


def test_runtime_credential_rotation_keeps_root_only_rollback(tmp_path):
    from scripts.rotate_runtime_credentials import rotate

    credentials = tmp_path / "credentials"
    credentials.mkdir(mode=0o700)
    current = credentials / "telegram_token"
    current.write_text("123456:old-token-value-long-enough\n", encoding="utf-8")
    current.chmod(0o600)
    incoming = tmp_path / "new-token"
    incoming.write_text("654321:new-token-value-long-enough\n", encoding="utf-8")
    incoming.chmod(0o600)
    rollback = tmp_path / "rollback"

    updated = rotate(
        credential_dir=credentials,
        rollback_root=rollback,
        telegram_token_file=incoming,
    )
    assert updated == ["telegram_token"]
    assert current.read_text(encoding="utf-8").strip().startswith("654321:")
    old = next(rollback.rglob("telegram_token"))
    assert old.stat().st_mode & 0o777 == 0o600
    assert old.read_text(encoding="utf-8").strip().startswith("123456:")


def test_purge_removes_managed_secrets_and_owner_id_only(tmp_path):
    from scripts.install_systemd_credentials import _purge_env

    env = tmp_path / ".env"
    env.write_text(
        "AIOS_TELEGRAM_TOKEN=secret\nTELEGRAM_CHAT_ID=123\nOPENROUTER_API_KEY=keep\n",
        encoding="utf-8",
    )
    _purge_env(env)
    value = env.read_text(encoding="utf-8")
    assert "AIOS_TELEGRAM_TOKEN" not in value
    assert "TELEGRAM_CHAT_ID" not in value
    assert "OPENROUTER_API_KEY=keep" in value
