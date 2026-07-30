"""Agent Ethical Boundary Guard for AIOS v11.63.0."""

from __future__ import annotations

import time
from typing import Any


class AgentEthicalBoundaryGuard:
    """Dynamic ethical boundary checker and taboo context filter."""

    def __init__(self) -> None:
        self.history: list[dict[str, Any]] = []

    def check_boundary(self, action_context: str) -> dict[str, Any]:
        safe = "malicious" not in action_context.lower() and "unauthorized" not in action_context.lower()
        result = {
            "action_context_snippet": action_context[:40],
            "ethically_safe": safe,
            "violation_detected": not safe,
            "timestamp": time.time(),
        }
        self.history.append(result)
        return result
