from dataclasses import dataclass


@dataclass
class AgentEvent:
    name: str
    payload: dict
