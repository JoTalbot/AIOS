"""AIOS Tool abstraction."""

from abc import ABC, abstractmethod


class Tool(ABC):
    name = "tool"

    @abstractmethod
    async def run(self, payload):
        raise NotImplementedError
