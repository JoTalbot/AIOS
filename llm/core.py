from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str):
        pass


class LLMCore:
    def __init__(self, provider=None):
        self.provider = provider

    async def ask(self, prompt):
        if not self.provider:
            return {"response": "no provider configured"}

        return await self.provider.generate(prompt)
