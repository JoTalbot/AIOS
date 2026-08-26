from abc import ABC, abstractmethod


class BaseAgent(ABC):

    def __init__(self, agent_id, memory=None):
        self.agent_id = agent_id
        self.memory = memory

    @abstractmethod
    async def think(self, goal):
        pass

    async def run(self, goal):
        result = await self.think(goal)

        if self.memory:
            self.memory.remember({
                "agent": self.agent_id,
                "goal": goal,
                "result": result
            })

        return result
