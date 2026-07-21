"""Auto-Scaler for AIOS"""

from typing import Dict


class AutoScaler:
    """Simple auto-scaling logic based on metrics."""

    def __init__(self, min_replicas: int = 1, max_replicas: int = 10):
        self.min_replicas = min_replicas
        self.max_replicas = max_replicas
        self.current_replicas = min_replicas

    def scale(self, cpu_usage: float, queue_size: int) -> int:
        if cpu_usage > 80 or queue_size > 50:
            self.current_replicas = min(self.current_replicas + 1, self.max_replicas)
        elif cpu_usage < 30 and queue_size < 5:
            self.current_replicas = max(self.current_replicas - 1, self.min_replicas)
        return self.current_replicas

    def stats(self) -> dict:
        return {
            "current": self.current_replicas,
            "min": self.min_replicas,
            "max": self.max_replicas
        }


auto_scaler = AutoScaler()