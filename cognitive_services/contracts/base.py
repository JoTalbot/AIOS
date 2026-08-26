from abc import ABC, abstractmethod
from typing import Any, Dict


class CognitiveServiceContract(ABC):
    """Base contract for AIOS cognitive services."""

    @property
    @abstractmethod
    def service_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    async def health(self) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError
