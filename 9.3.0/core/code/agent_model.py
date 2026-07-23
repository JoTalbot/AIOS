"""
AIOS Agent Model — Implementation based on docs/core/AIOS_AGENT_MODEL.md
Autonomous agent architecture for AIOS (JoTalbot/AIOS).
Without Octopus agent integration (~~/agents/).
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class AgentIdentity:
    agent_id: str  # Unique identity (immutable, per ARTICLE-I)
    role: str
    created_at: datetime
    version: str = "1.0"


@dataclass
class Capability:
    capability_id: str
    name: str
    description: str
    performance_score: float = 0.0
    version: str = "1.0"


@dataclass
class AgentMemory:
    short_term: List[str] = field(default_factory=list)  # Minutes → Hours
    operational: List[str] = field(default_factory=list)  # Running processes
    long_term_knowledge: Dict[str, str] = field(default_factory=dict)  # Structured knowledge


@dataclass
class Agent:
    identity: AgentIdentity
    goals: List[str]
    capabilities: List[Capability]
    memory: AgentMemory
    permissions: List[str] = field(default_factory=list)
    trust_level: float = 0.0
    experience_history: List[str] = field(default_factory=list)
    status: str = "active"

    def add_experience(self, experience: str) -> None:
        self.experience_history.append(experience)
        # Memory formation: observation → experience → memory (per AIOS_MEMORY_ARCHITECTURE.md)
        self.memory.operational.append(experience)

    def execute_goal(self, goal: str, worker_pool: List[str]) -> bool:
        # Agent plans, worker executes (Agent vs Worker separation)
        return len(worker_pool) > 0 and goal in self.goals

    def evolve(self, improvement: Dict) -> None:
        # Integration with Evolution Engine (AIOS_EVOLUTION_ENGINE.md)
        self.capabilities.append(
            Capability(
                capability_id=f"cap_{len(self.capabilities)}",
                name=improvement.get("name", "evolved_capability"),
                description=improvement.get("description", ""),
            )
        )
