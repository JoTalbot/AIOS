from abc import ABC, abstractmethod


class Agent(ABC):
    name = "base"

    @abstractmethod
    async def execute(self, task):
        raise NotImplementedError

    def status(self):
        return "ready"
