"""Structured handoff contract for OpenHands agent-to-agent execution."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgentHandoff:
    """Evidence-oriented result passed between agents."""

    status: str
    summary: str
    files_changed: tuple[str, ...] = ()
    commands_run: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    artifacts: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    next_action: str = ""
    verdict: str | None = None

    def validate(self, *, gate_role: bool = False) -> None:
        if not self.status.strip():
            raise ValueError("handoff status is required")
        if not self.summary.strip():
            raise ValueError("handoff summary is required")
        if gate_role and self.verdict not in {"APPROVED", "CHANGES_REQUESTED"}:
            raise ValueError("gate roles require exactly one valid verdict")

    def to_prompt(self) -> str:
        self.validate()
        sections = [
            f"STATUS: {self.status}",
            f"SUMMARY: {self.summary}",
            "FILES_CHANGED: " + (", ".join(self.files_changed) or "none"),
            "COMMANDS_RUN: " + (" | ".join(self.commands_run) or "none"),
            "EVIDENCE: " + (" | ".join(self.evidence) or "none"),
            "ARTIFACTS: " + (", ".join(self.artifacts) or "none"),
            "RISKS: " + (" | ".join(self.risks) or "none"),
            f"NEXT_ACTION: {self.next_action or 'none'}",
        ]
        if self.verdict is not None:
            sections.append(f"VERDICT: {self.verdict}")
        return "\n".join(sections)
