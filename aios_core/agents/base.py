from dataclasses import dataclass
from typing import Any


@dataclass
class AgentState:
    messages: list
    context: dict[str, Any]
    current_agent: str
    result: dict[str, Any] = None

class BaseAgent:
    def __init__(self, name: str):
        self.name = name

    async def process(self, state: AgentState) -> AgentState:
        raise NotImplementedError
