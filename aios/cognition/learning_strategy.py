"""Adaptive learning strategy layer."""


class LearningStrategy:
    def choose(self, context: dict) -> str:
        return "adapt"
