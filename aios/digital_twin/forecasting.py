"""Deterministic forecasting primitives for Digital Twin metrics."""

from typing import Iterable, List


def linear_forecast(values: Iterable[float], steps: int = 1) -> List[float]:
    values = list(values)
    if not values or steps <= 0:
        return []
    if len(values) == 1:
        slope = 0.0
    else:
        slope = values[-1] - values[-2]
    return [values[-1] + slope * i for i in range(1, steps + 1)]
