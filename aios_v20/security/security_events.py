from dataclasses import dataclass

@dataclass
class SecurityEvent:
    event_type: str
    source: str
    severity: str
    details: dict


SECURITY_EVENTS = [
    "access.denied",
    "threat.detected",
    "trust.changed",
    "policy.violation",
]
