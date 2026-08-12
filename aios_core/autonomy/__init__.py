"""AIOS Autonomy — единый автономный контур (Autonomous Decision Core).

Поток: вход -> intent -> planner (LLM-предложение) -> guardrails (решение)
       -> executor (исполнение) / escalate (владельцу) / reply.
"""
from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _env(key: str) -> str:
    """Прочитать systemd credential или явную переменную окружения."""
    if key in ("AIOS_TELEGRAM_TOKEN", "TELEGRAM_BOT_TOKEN"):
        from tg_bot.credentials import secret_from_env_or_credential

        value = secret_from_env_or_credential(
            "AIOS_TELEGRAM_TOKEN", "TELEGRAM_BOT_TOKEN", credential="telegram_token"
        )
        if value:
            return value
    if key in ("TELEGRAM_CHAT_ID", "AIOS_OWNER_CHAT_ID", "AIOS_AUTO_CODER_CHAT_ID"):
        from tg_bot.credentials import read_systemd_credential

        value = read_systemd_credential("telegram_owner_chat_id")
        if value:
            return value
    v = os.environ.get(key, "")
    if v:
        return v
    return ""


from .policy import AutonomyPolicy          # noqa: E402
from .journal import Journal                # noqa: E402
from .state import StateStore, Session       # noqa: E402
from .guardrails import Guardrails, Decision  # noqa: E402
from .planner import Planner                # noqa: E402
from .executor import Executor              # noqa: E402
from .loop import AutonomyCore              # noqa: E402

__all__ = [
    "AutonomyPolicy", "Journal", "StateStore", "Session",
    "Guardrails", "Decision", "Planner", "Executor", "AutonomyCore",
    "PROJECT_ROOT", "_env",
]
