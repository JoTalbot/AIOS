"""Compact cross-agent task memory for the OpenHands contour."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentMemoryEntry:
    role: str
    summary: str
    decisions: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)


@dataclass
class TaskMemory:
    """Bounded memory that passes useful facts, not whole conversations."""

    task_id: str
    entries: list[AgentMemoryEntry] = field(default_factory=list)
    max_entries: int = 12

    def add(self, entry: AgentMemoryEntry) -> None:
        self.entries.append(entry)
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries :]

    def compact_context(self, max_chars: int = 6000) -> str:
        lines = [f"Task memory: {self.task_id}"]
        for entry in self.entries:
            lines.append(f"[{entry.role}] {entry.summary}")
            if entry.decisions:
                lines.append("  decisions: " + "; ".join(entry.decisions))
            if entry.evidence:
                lines.append("  evidence: " + "; ".join(entry.evidence))
            if entry.files:
                lines.append("  files: " + ", ".join(entry.files))
            if entry.risks:
                lines.append("  risks: " + "; ".join(entry.risks))
        text = "\n".join(lines)
        return text if len(text) <= max_chars else text[-max_chars:]

    def repair_context(self) -> str:
        """Return only the latest actionable feedback for a repair iteration."""
        if not self.entries:
            return ""
        entry = self.entries[-1]
        lines = [f"Последняя проверка ({entry.role}): {entry.summary}"]
        if entry.decisions:
            lines.append("Замечания/решения: " + "; ".join(entry.decisions))
        if entry.evidence:
            lines.append("Доказательства: " + "; ".join(entry.evidence))
        if entry.risks:
            lines.append("Риски: " + "; ".join(entry.risks))
        return "\n".join(lines)
