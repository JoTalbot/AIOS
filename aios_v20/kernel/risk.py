from dataclasses import dataclass


@dataclass
class RiskAssessment:
    score: float
    level: str
    factors: list[str]


class RiskEngine:
    def assess(self, action, context=None):
        context = context or {}
        score = 0.0
        factors = []

        if action in {"deploy", "modify_system"}:
            score += 0.7
            factors.append("system_change")

        if context.get("external_access"):
            score += 0.2
            factors.append("external_access")

        level = "low"
        if score >= 0.7:
            level = "high"
        elif score >= 0.3:
            level = "medium"

        return RiskAssessment(score, level, factors)
