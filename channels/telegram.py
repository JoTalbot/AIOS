"""Telegram adapter foundation for AIOS."""

class TelegramChannel:
    async def receive(self, update):
        return update

    async def send(self, message):
        return message
