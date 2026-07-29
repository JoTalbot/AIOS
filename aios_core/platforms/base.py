"""Base Platform Adapter — абстрактный интерфейс для всех платформ."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class IncomingMessage:
    """Входящее сообщение с платформы."""
    message_id: str
    platform: str
    sender_id: str
    sender_name: str
    text: str
    timestamp: datetime
    metadata: dict[str, Any] = None

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
    
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.platform_name = self.__class__.__name__.replace("Adapter", "").lower()

    @abstractmethod
    async def receive_messages(self, since: datetime | None = None) -> list[IncomingMessage]:
        """Получить новые входящие сообщения."""

    @abstractmethod
    async def send_message(self, recipient_id: str, text: str, metadata: dict = None) -> SentMessage:
        """Отправить сообщение."""

    @abstractmethod
    async def mark_as_read(self, message_id: str) -> bool:
        """Пометить сообщение как прочитанное."""

    @abstractmethod
    async def get_user_info(self, user_id: str) -> dict[str, Any]:
        """Получить информацию о пользователе."""

    async def health_check(self) -> bool:
        """Проверить работоспособность соединения."""
        return True
