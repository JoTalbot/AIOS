"""Honest AI Training for AIOS"""

from typing import Dict, List


class HonestAI:
    """Trains AI systems to be honest by default."""

    def __init__(self):
        self.honesty_training_data: List[Dict] = []
        self.violations: List[Dict] = []

    def train_on_honesty(self, prompt: str, honest_response: str):
        self.honesty_training_data.append({
            "prompt": prompt,
            "honest_response": honest_response
        })

    def evaluate_honesty(self, response: str, ground_truth: str) -> float:
        if response == ground_truth:
            return 1.0
        self.violations.append({"response": response, "ground_truth": ground_truth})
        return 0.0

    def stats(self) -> dict:
        return {"training_examples": len(self.honesty_training_data)}