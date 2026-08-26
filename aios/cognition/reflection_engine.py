"""Self-reflection primitives for AIOS cognition."""

from dataclasses import dataclass, field


@dataclass
class ReflectionEngine:
    observations: list[dict] = field(default_factory=list)

    def reflect(self, observation: dict):
        self.observations.append(observation)
        return {"observation": observation, "status": "recorded"}
