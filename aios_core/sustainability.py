"""Sustainability & Green Computing for AIOS"""

from typing import Dict


class SustainabilityTracker:
    """Tracks carbon footprint and energy usage."""

    def __init__(self):
        self.energy_kwh = 0.0
        self.co2_kg = 0.0
        self.tasks_optimized = 0

    def record_task(self, cpu_seconds: float, energy_per_second: float = 0.0001):
        energy = cpu_seconds * energy_per_second
        self.energy_kwh += energy
        self.co2_kg += energy * 0.4  # rough estimate
        self.tasks_optimized += 1

    def optimize_suggestion(self) -> str:
        if self.co2_kg > 10:
            return "Consider scheduling tasks during low-carbon hours"
        return "Current usage is sustainable"

    def stats(self) -> dict:
        return {
            "energy_kwh": round(self.energy_kwh, 4),
            "co2_kg": round(self.co2_kg, 4),
            "tasks": self.tasks_optimized,
        }


sustainability = SustainabilityTracker()
