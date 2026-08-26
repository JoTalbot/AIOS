"""AIOS structured event logging foundation."""

import time


class RuntimeLogger:
    def __init__(self):
        self.events = []

    def info(self, message, **context):
        return self.emit("info", message, context)

    def error(self, message, **context):
        return self.emit("error", message, context)

    def emit(self, level, message, context=None):
        event = {
            "time": time.time(),
            "level": level,
            "message": message,
            "context": context or {}
        }
        self.events.append(event)
        return event

    def history(self):
        return self.events
