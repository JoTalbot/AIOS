"""AIOS channel adapter base."""

from abc import ABC, abstractmethod

class ChannelAdapter(ABC):
    @abstractmethod
    async def receive(self, payload):
        pass

    @abstractmethod
    async def send(self, response):
        pass
