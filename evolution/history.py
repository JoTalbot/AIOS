from datetime import datetime


class EvolutionHistory:

    def __init__(self):
        self.entries = []

    def record(self, version, result):
        self.entries.append({
            "version": version,
            "result": result,
            "time": datetime.utcnow()
        })

    def latest(self):
        return self.entries[-1] if self.entries else None
