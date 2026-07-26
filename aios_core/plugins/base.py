from abc import ABC, abstractmethod
from typing import Dict, Any, List

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
    async def initialize(self, config: Dict[str, Any]) -> bool:
        pass
    
    @abstractmethod
    async def execute(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        pass
