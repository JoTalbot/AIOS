"""Telegram execution flow foundation for AIOS."""


class TelegramFlow:
    def __init__(self, coordinator=None):
        self.coordinator = coordinator

    def handle(self, message):
        return self.coordinator.execute(message)
