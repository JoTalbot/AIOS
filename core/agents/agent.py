"""AIOS Agent base abstraction."""

from abc import ABC, abstractmethod


class Agent(ABC):
    name = "agent"
    capabilities = []

    async def initialize(self):
        return True

    @abstractmethod
    async def execute(self, context):
        raise NotImplementedError

    async def shutdown(self):
        return True
