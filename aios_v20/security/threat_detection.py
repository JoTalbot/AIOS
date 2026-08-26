from dataclasses import dataclass


@dataclass
class ThreatAssessment:
    score: float
    level: str
    factors: list[str]


class ThreatDetector:
    def assess(self, context: dict) -> ThreatAssessment:
        factors = []
        score = 0.0

        if context.get("external_access"):
            score += 0.4
            factors.append("external_access")

        if context.get("system_change"):
            score += 0.5
            factors.append("system_change")

        level = "LOW"
        if score >= 0.7:
            level = "HIGH"
        elif score >= 0.3:
            level = "MEDIUM"

        return ThreatAssessment(score, level, factors)
