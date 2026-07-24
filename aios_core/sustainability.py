"""Sustainability & Green Computing for AIOS v10.9.0.

Carbon footprint tracking, energy usage recording,
optimization suggestions, carbon offset estimation,
efficiency metrics, and sustainability reporting.

Classes:
    EnergyRecord  — energy usage record
    SustainabilityTracker — full sustainability engine
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Average carbon intensity: ~0.4 kg CO2 per kWh (global average)
CARBON_INTENSITY = 0.4


@dataclass
class EnergyRecord:
    """Energy usage record."""
    task_id: str = ""
    cpu_seconds: float = 0.0
    energy_kwh: float = 0.0
    co2_kg: float = 0.0
    optimized: bool = False
    timestamp: float = field(default_factory=time.time)


class SustainabilityTracker:
    """Full sustainability and green computing engine.

    Features:
    - Task energy recording
    - CO2 estimation
    - Optimization suggestions
    - Efficiency metrics
    - Sustainability reporting
    - Carbon offset estimation
    """

    def __init__(self, carbon_intensity: float = CARBON_INTENSITY) -> None:
        self.energy_kwh: float = 0.0
        self.co2_kg: float = 0.0
        self.tasks_optimized: int = 0
        self._carbon_intensity = carbon_intensity
        self._records: list[EnergyRecord] = []
        self._optimizations: list[dict[str, Any]] = []

    def record_task(self, cpu_seconds: float, energy_per_second: float = 0.0001,
                    task_id: str = "", optimized: bool = False) -> dict[str, Any]:
        """Record task energy usage (backward-compatible)."""
        energy = cpu_seconds * energy_per_second
        co2 = energy * self._carbon_intensity

        if optimized:
            energy *= 0.7  # 30% reduction for optimized tasks
            co2 *= 0.7
            self.tasks_optimized += 1

        self.energy_kwh += energy
        self.co2_kg += co2

        record = EnergyRecord(task_id=task_id, cpu_seconds=cpu_seconds,
                             energy_kwh=round(energy, 8), co2_kg=round(co2, 8),
                             optimized=optimized)
        self._records.append(record)
        return {"energy_kwh": round(energy, 8), "co2_kg": round(co2, 8), "optimized": optimized}

    def optimize_suggestion(self) -> str:
        """Return optimization suggestion (backward-compatible)."""
        if self.co2_kg > 10:
            return "Consider scheduling tasks during low-carbon hours (renewable energy peak)"
        elif self.energy_kwh > 5:
            return "Batch similar tasks together to reduce total CPU time"
        elif self.tasks_optimized < 5:
            return "Enable task optimization to reduce energy by 30%"
        return "Current usage is sustainable"

    def carbon_offset_needed(self) -> float:
        """Estimate carbon offset needed to neutralize footprint."""
        return round(self.co2_kg, 4)

    def efficiency_score(self) -> float:
        """Compute efficiency score (optimized vs total tasks)."""
        total = len(self._records)
        if total == 0:
            return 1.0
        optimized_count = sum(1 for r in self._records if r.optimized)
        return round(optimized_count / total, 4)

    def sustainability_report(self) -> dict[str, Any]:
        """Generate a full sustainability report."""
        avg_energy_per_task = self.energy_kwh / max(len(self._records), 1)
        avg_co2_per_task = self.co2_kg / max(len(self._records), 1)

        return {
            "total_energy_kwh": round(self.energy_kwh, 6),
            "total_co2_kg": round(self.co2_kg, 6),
            "tasks_total": len(self._records),
            "tasks_optimized": self.tasks_optimized,
            "efficiency_score": self.efficiency_score(),
            "avg_energy_per_task": round(avg_energy_per_task, 8),
            "avg_co2_per_task": round(avg_co2_per_task, 8),
            "optimization_tip": self.optimize_suggestion(),
        }

    def stats(self) -> dict[str, Any]:
        """Return summary statistics (backward-compatible)."""
        return {
            "energy_kwh": round(self.energy_kwh, 4),
            "co2_kg": round(self.co2_kg, 4),
            "tasks": len(self._records),
            "optimized": self.tasks_optimized,
            "efficiency": self.efficiency_score(),
        }


sustainability = SustainabilityTracker()
