"""AIOS v20 agent primitive.

Minimal foundation for future agent lifecycle management.
"""

from dataclasses import dataclass, field


@dataclass
class Agent:
    """Autonomous AIOS execution entity."""

    name: str
    role: str = "general"
    skills: list[str] = field(default_factory=list)
    goals: list[str] = field(default_factory=list)
    evolution_enabled: bool = True

    def describe(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "skills": self.skills,
            "goals": self.goals,
            "evolution_enabled": self.evolution_enabled,
        }
