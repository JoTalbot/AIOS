"""AIOS Autonomy — единый автономный контур (Autonomous Decision Core).

Поток: вход -> intent -> planner (LLM-предложение) -> guardrails (решение)
       -> executor (исполнение) / escalate (владельцу) / reply.
"""
from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _env(key: str) -> str:
    """Прочитать переменную окружения или из .env."""
    v = os.environ.get(key, "")
    if v:
        return v
    p = PROJECT_ROOT / ".env"
    if p.exists():
        try:
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith(key + "="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
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
