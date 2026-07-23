"""Honest AI Training for AIOS"""

from typing import Dict, List


class HonestAI:
    """Trains AI systems to be honest by default — collects examples and evaluates truthfulness."""

    def __init__(self):
        self.honesty_training_data: List[Dict] = []
        self.violations: List[Dict] = []

    def train_on_honesty(self, prompt: str, honest_response: str):
        """Store a *(prompt, honest_response)* training pair."""
        self.honesty_training_data.append({"prompt": prompt, "honest_response": honest_response})

    def evaluate_honesty(self, response: str, ground_truth: str) -> float:
        """Return 1.0 if *response* matches *ground_truth*, else 0.0 and log a violation."""
        if response == ground_truth:
            return 1.0
        self.violations.append({"response": response, "ground_truth": ground_truth})
        return 0.0

    def stats(self) -> dict:
        """Return number of collected training examples."""
        return {"training_examples": len(self.honesty_training_data)}
