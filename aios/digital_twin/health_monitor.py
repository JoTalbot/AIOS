"""Health evaluation layer for Digital Twin state."""

from typing import Dict


class TwinHealthMonitor:
    def evaluate(self, state: Dict[str, float]) -> Dict[str, str]:
        result = {}
        for key, value in state.items():
            result[key] = "healthy" if value >= 0 else "warning"
        return result
