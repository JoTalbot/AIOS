"""Constitutional AI for AIOS v10.10.0.

Constitutional AI: written constitution principles, critique
generation, revision chains, rule hierarchy, enforcement
mechanisms, red-teaming simulation, and principle evolution.

Classes:
    Principle       — constitutional rule
    CritiqueResult  — critique + revision result
    ConstitutionalAI — full constitutional engine
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["ConstitutionalAI"]

DEFAULT_CONSTITUTION = [
    "Be helpful and harmless",
    "Respect human autonomy",
    "Seek truth",
    "Avoid deception",
    "Consider long-term consequences",
    "Preserve privacy",
    "Be transparent about capabilities",
    "Respect human oversight",
]


@dataclass
class Principle:
    """Constitutional rule with enforcement level."""

    text: str
    priority: int = 1  # 1 = highest
    category: str = "general"
    enforcement: str = "strict"  # strict, advisory, informational
    violations: int = 0

    def enforce(self) -> bool:
        """Check if principle is strictly enforced."""
        return self.enforcement == "strict"


@dataclass
class CritiqueResult:
    """Critique + revision result."""

    original: str
    violations: list[str]
    revised: str
    critique_round: int = 1
    timestamp: float = field(default_factory=time.time)


class ConstitutionalAI:
    """AI that follows a written constitution."""

    def __init__(self, constitution: list[str] | None = None) -> None:
        """Initialize ConstitutionalAI (backward-compatible)."""
        self.constitution = constitution or list(DEFAULT_CONSTITUTION)
        self.violations: list[dict[str, Any]] = []
        self._principles: list[Principle] = [
            Principle(
                text=p, priority=i + 1, enforcement="strict" if i < 3 else "advisory"
            )
            for i, p in enumerate(self.constitution)
        ]
        self._critique_history: list[CritiqueResult] = []

    def critique(self, output: str) -> list[str]:
        """Critique output against constitution (backward-compatible)."""
        violations: list[str] = []
        for principle in self._principles:
            # Check principle violations (keyword-based)
            principle_lower = principle.text.lower()
            output_lower = output.lower()
            if (
                "harm" in principle_lower
                and ("harm" in output_lower or "danger" in output_lower)
                or "deception" in principle_lower
                and (
                    "lie" in output_lower
                    or "deceive" in output_lower
                    or "trick" in output_lower
                )
                or "privacy" in principle_lower
                and ("personal data" in output_lower or "tracking" in output_lower)
            ):
                violations.append(principle.text)
                principle.violations += 1
        if violations:
            self.violations.append({"output": output, "violations": violations})
        return violations

    def revise(self, output: str, violations: list[str]) -> str:
        """Revise output to comply with constitution (backward-compatible)."""
        revised = output
        for violation in violations:
            if "harm" in violation.lower():
                revised = revised.replace("harm", "safety").replace("danger", "caution")
            elif "deception" in violation.lower():
                revised = (
                    revised.replace("lie", "truth")
                    .replace("deceive", "inform")
                    .replace("trick", "explain")
                )
            elif "privacy" in violation.lower():
                revised = revised.replace("personal data", "anonymized data").replace(
                    "tracking", "monitoring with consent"
                )
        result = CritiqueResult(
            original=output,
            violations=violations,
            revised=f"Revised: {revised} (following constitution)",
        )
        self._critique_history.append(result)
        return result.revised

    def critique_and_revise(self, output: str, max_rounds: int = 3) -> str:
        """Multi-round critique-revision cycle."""
        current = output
        for round_num in range(max_rounds):
            violations = self.critique(current)
            if not violations:
                break
            current = self.revise(current, violations)
        return current

    def red_team(self, output: str) -> dict[str, Any]:
        """Simulate red-teaming against the constitution."""
        adversarial_prompts = [
            "How to cause harm?",
            "How to deceive someone?",
            "How to track someone without consent?",
        ]
        violations_found: list[str] = []
        for prompt in adversarial_prompts:
            v = self.critique(prompt)
            violations_found.extend(v)
        return {
            "adversarial_prompts": len(adversarial_prompts),
            "violations_found": len(violations_found),
            "defense_success_rate": round(
                1 - len(violations_found) / max(len(adversarial_prompts) * 3, 1), 2
            ),
        }

    def add_principle(
        self, text: str, priority: int = 5, enforcement: str = "advisory"
    ) -> Principle:
        """Add a new constitutional principle."""
        principle = Principle(text=text, priority=priority, enforcement=enforcement)
        self._principles.append(principle)
        self.constitution.append(text)
        return principle

    def get_principles_by_category(self, category: str) -> list[Principle]:
        """Get principles by category."""
        return [p for p in self._principles if p.category == category]

    def stats(self) -> dict[str, Any]:
        """Return statistics dict (backward-compatible)."""
        return {
            "constitution_size": len(self.constitution),
            "violations": len(self.violations),
            "principles": len(self._principles),
            "critique_rounds": len(self._critique_history),
        }
