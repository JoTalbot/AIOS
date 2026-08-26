from abc import ABC, abstractmethod

class Agent(ABC):
    @abstractmethod
    async def execute(self, context):
        raise NotImplementedError

class Tool(ABC):
    @abstractmethod
    async def run(self, payload):
        raise NotImplementedError

class Memory(ABC):
    @abstractmethod
    async def store(self, item):
        raise NotImplementedError

    @abstractmethod
    async def retrieve(self, query):
        raise NotImplementedError
