from abc import ABC, abstractmethod
from typing import Any


class BasePlugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        pass

    @abstractmethod
    async def initialize(self, config: dict[str, Any]) -> bool:
        pass

    @abstractmethod
    async def execute(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        pass
