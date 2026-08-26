"""Structured logging foundation."""

class RuntimeLogger:
    def info(self, message, **context):
        return {"level": "info", "message": message, "context": context}

    def error(self, message, **context):
        return {"level": "error", "message": message, "context": context}
