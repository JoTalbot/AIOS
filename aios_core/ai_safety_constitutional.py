"""Constitutional AI for AIOS"""

from typing import Dict, List

__all__ = ["ConstitutionalAI"]


class ConstitutionalAI:
    """AI that follows a written constitution."""

    def __init__(self, constitution: list[str] = None):
        """Initialize ConstitutionalAI."""
        self.constitution = constitution or [
            "Be helpful and harmless",
            "Respect human autonomy",
            "Seek truth",
            "Avoid deception",
            "Consider long-term consequences",
        ]
        self.violations: List[Dict] = []

    def critique(self, output: str) -> list[str]:
        """Execute critique."""
        violations = []
        for principle in self.constitution:
            if "harm" in principle.lower() and "harm" in output.lower():
                violations.append(principle)
        if violations:
            self.violations.append({"output": output, "violations": violations})
        return violations

    def revise(self, output: str, violations: list[str]) -> str:
        """Execute revise."""
        return f"Revised: {output} (following constitution)"

    def stats(self) -> dict:
        """Return statistics dict."""
        return {
            "constitution_size": len(self.constitution),
            "violations": len(self.violations),
        }
