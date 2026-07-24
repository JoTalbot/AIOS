"""
AIOS Memory Architecture — Implementation based on docs/core/AIOS_MEMORY_ARCHITECTURE.md
Autonomous memory system for AIOS. Without Octopus integration (~/agents/).
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MemoryObservation:
    observation_id: str
    timestamp: datetime
    content: str
    source_agent_id: str | None = None


@dataclass
class Experience:
    experience_id: str
    observations: list[MemoryObservation]
    formed_at: datetime
    context: str = ""


@dataclass
class KnowledgeObject:
    knowledge_id: str
    title: str
    content: str
    source_experience_ids: list[str]
    validity_score: float = 1.0
    version: str = "1.0"


@dataclass
class AIOSMemory:
    # Memory layers (per AIOS_MEMORY_ARCHITECTURE.md)
    short_term_memory: list[str] = field(default_factory=list)  # Minutes → Hours
    operational_memory: list[str] = field(default_factory=list)  # Running processes
    long_term_knowledge: dict[str, KnowledgeObject] = field(default_factory=dict)
    experience_ledger: list[Experience] = field(default_factory=list)

    def observe(self, observation: MemoryObservation) -> None:
        # Nothing changes silently (per AIOS_EVENT_SYSTEM.md principle)
        self.short_term_memory.append(observation.content)

    def form_memory(self, observations: list[MemoryObservation], context: str = "") -> Experience:
        experience = Experience(
            experience_id=f"exp_{len(self.experience_ledger)}",
            observations=observations,
            formed_at=datetime.now(),
            context=context,
        )
        self.experience_ledger.append(experience)
        # Memory formation: observation → experience → memory (per architecture)
        return experience

    def update_knowledge(self, knowledge: KnowledgeObject) -> None:
        self.long_term_knowledge[knowledge.knowledge_id] = knowledge
