"""Base Platform Adapter — абстрактный интерфейс для всех платформ."""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class IncomingMessage:
    """Входящее сообщение с платформы."""
    message_id: str
    platform: str
    sender_id: str
    sender_name: str
    text: str
    timestamp: datetime
    metadata: Dict[str, Any] = None

@dataclass
class SentMessage:
    """Отправленное сообщение."""
    message_id: str
    platform: str
    recipient_id: str
    text: str
    timestamp: datetime
    status: str = "sent"  # sent, delivered, failed

class PlatformAdapter(ABC):
    """Абстрактный базовый класс для всех платформ."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.platform_name = self.__class__.__name__.replace("Adapter", "").lower()

    @abstractmethod
    async def receive_messages(self, since: Optional[datetime] = None) -> List[IncomingMessage]:
        """Получить новые входящие сообщения."""
        pass

    @abstractmethod
    async def send_message(self, recipient_id: str, text: str, metadata: Dict = None) -> SentMessage:
        """Отправить сообщение."""
        pass

    @abstractmethod
    async def mark_as_read(self, message_id: str) -> bool:
        """Пометить сообщение как прочитанное."""
        pass

    @abstractmethod
    async def get_user_info(self, user_id: str) -> Dict[str, Any]:
        """Получить информацию о пользователе."""
        pass

    async def health_check(self) -> bool:
        """Проверить работоспособность соединения."""
        return True
