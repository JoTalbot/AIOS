from dataclasses import dataclass
from typing import Callable, Dict


@dataclass
class Tool:
    name: str
    handler: Callable
    permission: str = "default"


class ToolKernel:
    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        self.tools[tool.name] = tool

    async def execute(self, name, *args, **kwargs):
        tool = self.tools.get(name)
        if not tool:
            raise ValueError(f"Tool not found: {name}")
        return await tool.handler(*args, **kwargs)
