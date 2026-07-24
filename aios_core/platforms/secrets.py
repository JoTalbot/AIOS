"""Secrets — учётные данные платформ через окружение, никогда в код/БД.

Паттерн guarded-by-design: логины/пароли (например, аккаунты Instagram)
хранятся в env-переменных или локальном ``secrets.env`` (в
``.gitignore``), но не в репозитории, не в SQLite и не в логах.

Именование (верхний регистр, ``-`` → ``_``):

* ``AIOS_SECRET__<PLATFORM>__<FIELD>`` — секрет платформы;
* ``AIOS_SECRET__<PLATFORM>__<PROFILE>__<FIELD>`` — секрет профиля
  (приоритет над платформенным).

Пример для Instagram::

    export AIOS_SECRET__INSTAGRAM__USERNAME='jo.talbot@gmail.com'
    export AIOS_SECRET__INSTAGRAM__PASSWORD='•••'
    # пароль профиля work:
    export AIOS_SECRET__INSTAGRAM__WORK__PASSWORD='•••'
"""

from __future__ import annotations

import os
from pathlib import Path

_ENV_PREFIX = "AIOS_SECRET__"
DEFAULT_SECRETS_FILE = "data/secrets.env"


def _norm(value: str) -> str:
    return value.upper().replace("-", "_")


def env_name(platform: str, field: str, profile: str | None = None) -> str:
    """Имя env-переменной секрета (для сообщений об ошибках/доки)."""
    parts = [_ENV_PREFIX + _norm(platform)]
    if profile:
        parts.append(_norm(profile))
    parts.append(_norm(field))
    return "__".join(parts)


def secret(
    platform: str,
    field: str,
    profile: str | None = None,
    default: str | None = None,
) -> str | None:
    """Читает секрет из окружения (профильный приоритетнее)."""
    if profile:
        value = os.environ.get(env_name(platform, field, profile))
        if value:
            return value
    return os.environ.get(env_name(platform, field)) or default


def required_secret(
    platform: str,
    field: str,
    profile: str | None = None,
) -> str:
    """Секрет или понятная ошибка — с именем переменной, без значения."""
    value = secret(platform, field, profile)
    if not value:
        names = env_name(platform, field, profile)
        if profile:
            names += f" или {env_name(platform, field)}"
        raise ValueError(
            f"secret not configured: set {names} "
            "(values are read from env only, never stored)"
        )
    return value


def load_secrets_file(
    path: str | None = None,
    override: bool = False,
) -> int:
    """Подгружает KEY=VALUE строки в окружение (по умолчанию не затирая).

    Путь: явный ``path`` → env ``AIOS_SECRETS_FILE`` →
    ``data/secrets.env``. Пустые строки и ``#``-комментарии
    игнорируются. Возвращает число применённых переменных; отсутствующий
    файл — 0 (не ошибка).
    """
    target = Path(path or os.environ.get("AIOS_SECRETS_FILE") or DEFAULT_SECRETS_FILE)
    if not target.exists():
        return 0
    applied = 0
    for raw in target.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip("\"'")
        if key and (override or key not in os.environ):
            os.environ[key] = value
            applied += 1
    return applied
