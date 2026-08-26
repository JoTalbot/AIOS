"""Curiosity-driven exploration layer."""


class CuriosityEngine:
    def score(self, unknown: str) -> float:
        return 0.5 if unknown else 0.0
