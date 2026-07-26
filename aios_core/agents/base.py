from typing import Dict, Any
from dataclasses import dataclass

@dataclass
class AgentState:
    messages: list
    context: Dict[str, Any]
    current_agent: str
    result: Dict[str, Any] = None

class BaseAgent:
    def __init__(self, name: str):
        self.name = name

    async def process(self, state: AgentState) -> AgentState:
        raise NotImplementedError
