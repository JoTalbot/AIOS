from dataclasses import dataclass

@dataclass
class Incident:
    source: str
    severity: int
    message: str

class IncidentResponseEngine:
    def analyze(self, incident):
        return {
            "action": "recover" if incident.severity > 5 else "monitor",
            "source": incident.source
        }
