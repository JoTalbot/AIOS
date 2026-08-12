#!/usr/bin/env python3
"""Migrate AIOS runtime secrets into root-only systemd credential sources.

No secret values are printed. Existing credential files are preserved when the
corresponding legacy environment value is absent. ``--purge-managed-env`` is
opt-in because other legacy jobs may still consume the shared .env file.
"""

from __future__ import annotations

import argparse
import os
import secrets
import tempfile
from pathlib import Path

from cryptography.fernet import Fernet

ROOT = Path(os.environ.get("AIOS_ROOT", "/root/AIOS"))
SOURCE_DIR = Path(os.environ.get("AIOS_CREDENTIAL_SOURCE_DIR", "/etc/aios/credentials"))
MANAGED_ENV_KEYS = {
    "AIOS_TELEGRAM_TOKEN",
    "TELEGRAM_BOT_TOKEN",
    "COLAB_LLM_API_KEY",
    "TAILSCALE_AUTH_KEY",
    "TELEGRAM_CHAT_ID",
    "TELEGRAM_CANARY_CHAT_ID",
    "TELEGRAM_ALERT_CHAT_ID",
    "AIOS_OWNER_CHAT_ID",
    "AIOS_AUTO_CODER_CHAT_ID",
}


def _parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return values
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        values[key.strip()] = value
    return values


def _atomic(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    tmp = Path(name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(value.rstrip(b"\n") + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _existing(name: str) -> bytes:
    try:
        return (SOURCE_DIR / name).read_bytes().strip()
    except OSError:
        return b""


def _write_if_value(name: str, value: str) -> None:
    target = SOURCE_DIR / name
    if value:
        _atomic(target, value.encode("utf-8"))
    elif not target.exists():
        _atomic(target, b"")


def _update_env(path: Path, values: dict[str, str]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    remaining = dict(values)
    updated: list[str] = []
    for line in lines:
        key = line.partition("=")[0].strip() if "=" in line else ""
        if key in remaining:
            updated.append(f"{key}={remaining.pop(key)}")
        else:
            updated.append(line)
    updated.extend(f"{key}={value}" for key, value in remaining.items())
    _atomic(path, ("\n".join(updated) + "\n").encode("utf-8"))


def _purge_env(path: Path) -> None:
    if not path.exists():
        return
    kept = [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.partition("=")[0].strip() not in MANAGED_ENV_KEYS
    ]
    _atomic(path, ("\n".join(kept) + ("\n" if kept else "")).encode("utf-8"))


def _migrate_canary_settings(source: Path, destination: Path) -> None:
    """Move non-sensitive canary thresholds into /etc without chat metadata."""
    if not source.exists():
        if not destination.exists():
            _atomic(destination, b"")
        return
    kept = [
        line
        for line in source.read_text(encoding="utf-8").splitlines()
        if line.partition("=")[0].strip() not in MANAGED_ENV_KEYS
    ]
    _atomic(destination, ("\n".join(kept) + ("\n" if kept else "")).encode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--purge-managed-env", action="store_true")
    args = parser.parse_args()

    env_file = ROOT / ".env"
    values = _parse_env(env_file)
    service_values = _parse_env(
        Path(os.environ.get("AIOS_TELEGRAM_ENV_FILE", "/etc/aios/aios-telegram-bot.env"))
    )
    keeper_values = _parse_env(ROOT / "data" / ".colab_llm.env")
    existing_token = _existing("telegram_token").decode("utf-8")
    token = (
        existing_token
        or service_values.get("AIOS_TELEGRAM_TOKEN")
        or service_values.get("TELEGRAM_BOT_TOKEN")
        or values.get("AIOS_TELEGRAM_TOKEN")
        or values.get("TELEGRAM_BOT_TOKEN", "")
    )
    if not token:
        raise RuntimeError("Telegram token is absent; credential migration aborted")
    _write_if_value("telegram_token", token)

    existing_queue_key = _existing("telegram_queue_key")
    legacy_queue_key = ROOT / "data" / "credentials" / "telegram_queue.key"
    if existing_queue_key:
        queue_key = existing_queue_key
    elif legacy_queue_key.exists():
        queue_key = legacy_queue_key.read_bytes().strip()
    else:
        queue_key = Fernet.generate_key()
    _atomic(SOURCE_DIR / "telegram_queue_key", queue_key)

    existing_offsite_key = _existing("telegram_offsite_backup_key")
    if existing_offsite_key:
        offsite_key = existing_offsite_key
    else:
        import base64

        offsite_key = base64.urlsafe_b64encode(os.urandom(32))
    _atomic(SOURCE_DIR / "telegram_offsite_backup_key", offsite_key)
    _write_if_value("b2_access_key_id", "")
    _write_if_value("b2_secret_access_key", "")

    existing_colab_key = _existing("colab_llm_api_key").decode("utf-8")
    colab_key = (
        existing_colab_key
        or keeper_values.get("COLAB_LLM_API_KEY")
        or values.get("COLAB_LLM_API_KEY", "")
    )
    if not colab_key:
        colab_key = secrets.token_urlsafe(36)
    _write_if_value("colab_llm_api_key", colab_key)

    existing_tailscale_key = _existing("tailscale_auth_key").decode("utf-8")
    tailscale_key = existing_tailscale_key or values.get("TAILSCALE_AUTH_KEY", "")
    _write_if_value("tailscale_auth_key", tailscale_key)

    canary_env = ROOT / "data" / ".telegram_canary.env"
    canary_values = _parse_env(canary_env)
    _migrate_canary_settings(canary_env, Path("/etc/aios/telegram-canary.env"))
    owner_chat = (
        _existing("telegram_owner_chat_id").decode("utf-8")
        or service_values.get("TELEGRAM_CHAT_ID")
        or values.get("TELEGRAM_CHAT_ID", "")
        or canary_values.get("TELEGRAM_CANARY_CHAT_ID", "")
        or canary_values.get("TELEGRAM_ALERT_CHAT_ID", "")
    ).split(",", 1)[0].strip()
    if owner_chat:
        try:
            int(owner_chat)
        except ValueError as exc:
            raise RuntimeError("Telegram owner chat ID is invalid") from exc
        _write_if_value("telegram_owner_chat_id", owner_chat)

    if args.purge_managed_env:
        _purge_env(env_file)
        _purge_env(
            Path(os.environ.get("AIOS_TELEGRAM_ENV_FILE", "/etc/aios/aios-telegram-bot.env"))
        )
        _purge_env(Path("/etc/aios/aios-auto-coder.env"))
        _purge_env(ROOT / "data" / ".telegram_canary.env")
        (ROOT / "data" / ".colab_llm.env").unlink(missing_ok=True)

    os.chmod(SOURCE_DIR, 0o700)
    print("systemd_credentials=installed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
