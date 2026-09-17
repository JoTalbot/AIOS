from abc import ABC, abstractmethod
from .llm_balancer import llm_balancer

class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str):
        pass

class LLMCore:
    def __init__(self, provider=None):
        self.provider = provider or llm_balancer

    async def ask(self, prompt, system=None):
        if hasattr(self.provider, 'ask'):
            return await self.provider.ask(prompt, system=system)
        return await self.provider.generate(prompt)
