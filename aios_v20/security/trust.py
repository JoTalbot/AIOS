from dataclasses import dataclass


@dataclass
class TrustScore:
    value: float
    reason: list[str]


class TrustManager:
    def evaluate(self, agent: dict) -> TrustScore:
        score = 0.5
        reasons = []

        if agent.get("verified"):
            score += 0.3
            reasons.append("verified")

        if agent.get("history_clean"):
            score += 0.2
            reasons.append("clean_history")

        return TrustScore(min(score, 1.0), reasons)
