from datetime import datetime


class AuditLog:
    def __init__(self):
        self.events = []

    def record(self, actor: str, action: str, result: str):
        self.events.append({
            "time": datetime.utcnow().isoformat(),
            "actor": actor,
            "action": action,
            "result": result,
        })
