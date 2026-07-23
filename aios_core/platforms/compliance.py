"""Compliance-контур: принуждение ToS-флагов дескриптора на действиях.

Каждая платформа декларирует в ``platforms/<name>.yaml`` блок
``extras.compliance`` (правовая/ToS-политика площадки)::

    extras:
      compliance:
        autopost_allowed: false     # разрешён ли автопостинг с confirm
        messenger: approval-only    # approval-only | open | none
        collector: true             # разрешён ли read-only сбор ленты
        actions_per_hour: 60        # необязательный rate-limit
        note: "..."                 # человекочитаемое обоснование

Guarded-перевод флагов на действия агента:

* ``autopost`` — публикация постов/объявлений даже с явным confirm —
  только при ``autopost_allowed: true``;
* ``collect`` — сбор публичной ленты (read-only) — только при
  ``collector: true``;
* ``send`` — постановка ответа в guarded outbox — всегда, кроме
  ``messenger: none`` (очередь сама по себе устройство не трогает);
* ``auto_send`` — прямая запись на устройство в обход outbox —
  только при ``messenger: open``.

Платформа без блока compliance честно считается «не задекларировала
правовую позицию» → guarded-действия запрещены (кроме ``send``, т.е.
черновик в очередь). scaffold генерирует deny-by-default блок сразу.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import yaml

ACTIONS = ("autopost", "collect", "send", "auto_send")


def compliance_block(platform: str, directory: str = "platforms") -> Dict[str, object]:
    """Читает ``extras.compliance`` дескриптора ({} при отсутствии)."""
    yaml_path = Path(directory) / f"{platform}.yaml"
    if not yaml_path.exists():
        return {}
    doc = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    block = (doc.get("extras") or {}).get("compliance") or {}
    return dict(block) if isinstance(block, dict) else {}


def compliance_guard(
    platform: str,
    action: str,
    directory: str = "platforms",
) -> Dict[str, object]:
    """Проверяет, разрешено ли ``action`` политикой платформы.

    Args:
        platform: имя платформы (``platforms/<name>.yaml``).
        action: одно из :data:`ACTIONS`.
        directory: каталог дескрипторов.

    Returns:
        {platform, action, allowed, reason, policy}.

    Raises:
        ValueError: неизвестное действие (честная ошибка, не silently).
    """
    if action not in ACTIONS:
        raise ValueError(
            f"unknown compliance action '{action}': " f"expected one of {list(ACTIONS)}"
        )
    block = compliance_block(platform, directory)
    policy_declared = bool(block)
    note = str(block.get("note") or "")

    if action == "autopost":
        allowed = policy_declared and bool(block.get("autopost_allowed"))
        reason = (
            "autopost_allowed: true"
            if allowed
            else "автопостинг запрещён compliance (%s)"
            % (note or "autopost_allowed не задан — deny by default")
        )
    elif action == "collect":
        allowed = policy_declared and bool(block.get("collector"))
        reason = (
            "collector: true"
            if allowed
            else "сбор ленты запрещён compliance (%s)"
            % (note or "collector не задан — deny by default")
        )
    elif action == "send":
        messenger = str(block.get("messenger") or "")
        allowed = not policy_declared or messenger != "none"
        reason = (
            "draft в outbox (approval-only)"
            if messenger == "approval-only"
            else (
                "мессенджер отключён compliance (messenger: none)"
                if not allowed
                else "мессенджер разрешён"
            )
        )
    else:  # auto_send
        messenger = str(block.get("messenger") or "")
        allowed = policy_declared and messenger == "open"
        reason = (
            "messenger: open — прямая отправка разрешена"
            if allowed
            else "прямая отправка запрещена: messenger=%s — только guarded "
            "outbox + flush после одобрения" % (messenger or "не задан")
        )

    return {
        "platform": platform,
        "action": action,
        "allowed": bool(allowed),
        "reason": reason,
        "policy": block,
    }


def rate_limit_hours(platform: str, directory: str = "platforms") -> Optional[int]:
    """Rate-limit платформы (действий/час) из compliance, если задан."""
    value = compliance_block(platform, directory).get("actions_per_hour")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
