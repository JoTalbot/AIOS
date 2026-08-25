"""Аудит-события OpenHands-контура поверх ``aios_core.audit_logger.AuditLogger``.

Все значения проходят маскирование секретов до записи: в лог не попадают
passwords, tokens, API keys, private keys, cookies (Этап 17 master-плана).
"""

import re
from typing import Any

from aios_core.audit_logger import AuditLogger

from .models import AgentRole

EVENT_PREFIX = "openhands"

# Ключи, значения которых маскируются всегда.
_SENSITIVE_KEY = re.compile(
    r"(password|passwd|secret|token|api[_-]?key|private[_-]?key|cookie|credential|authorization)",
    re.IGNORECASE,
)
# Значения, похожие на секреты: длинные base64/hex-строки (≥20 символов).
_SENSITIVE_VALUE = re.compile(r"\b[A-Za-z0-9+/=_-]{20,}\b")

MASK = "***"


def mask_secrets(obj: Any) -> Any:
    """Рекурсивно замаскировать секреты в dict/list/str перед записью в лог."""
    if isinstance(obj, dict):
        masked = {}
        for key, value in obj.items():
            if _SENSITIVE_KEY.search(str(key)):
                masked[key] = MASK
            else:
                masked[key] = mask_secrets(value)
        return masked
    if isinstance(obj, (list, tuple)):
        return [mask_secrets(item) for item in obj]
    if isinstance(obj, str):
        return _SENSITIVE_VALUE.sub(MASK, obj)
    return obj


class OHAuditLogger:
    """Обёртка над AuditLogger: контурный тип события + маскирование секретов."""

    def __init__(self, logger: AuditLogger | None = None) -> None:
        self._logger = logger or AuditLogger()

    def log(
        self,
        action: str,
        task_id: str,
        agent: AgentRole | str,
        **fields: Any,
    ) -> dict:
        """Записать событие контура (тип ``openhands.<action>``) с маскированием."""
        role = agent.value if isinstance(agent, AgentRole) else str(agent)
        event = {
            "type": f"{EVENT_PREFIX}.{action}",
            "task_id": task_id,
            "agent": role,
            **fields,
        }
        return self._logger.record(mask_secrets(event))

    def log_transition(self, task_id: str, agent: AgentRole | str, src: str, dst: str, **fields: Any) -> dict:
        """Событие смены статуса задачи."""
        return self.log("transition", task_id, agent, src=src, dst=dst, **fields)

    def log_decision(self, task_id: str, agent: AgentRole | str, decision: str, **fields: Any) -> dict:
        """Событие решения (gate, review, retry, fail)."""
        return self.log("decision", task_id, agent, decision=decision, **fields)

    @property
    def backend(self) -> AuditLogger:
        """Нижележащий AuditLogger (для query/stats)."""
        return self._logger
