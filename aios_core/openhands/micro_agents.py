"""Specialized verification roles used by the meta-review stage."""

from __future__ import annotations

from dataclasses import dataclass
from .models import AgentRole


@dataclass(frozen=True)
class MicroAgentSpec:
    name: str
    role: AgentRole
    purpose: str
    required_for: tuple[str, ...] = ()


MICRO_AGENTS = (
    MicroAgentSpec("architecture", AgentRole.REVIEWER, "Совместимость архитектуры и scope", ("feature", "refactor")),
    MicroAgentSpec("security", AgentRole.SECURITY, "Угрозы, secrets, injection и auth", ("security", "feature")),
    MicroAgentSpec("quality", AgentRole.QA, "Функциональные и regression-сценарии", ("feature", "bugfix")),
    MicroAgentSpec("tests", AgentRole.TESTER, "Качество тестового покрытия и assertions", ("feature", "bugfix", "refactor")),
)


def select_micro_agents(task_type: str) -> tuple[MicroAgentSpec, ...]:
    selected = tuple(agent for agent in MICRO_AGENTS if not agent.required_for or task_type in agent.required_for)
    return selected or MICRO_AGENTS
