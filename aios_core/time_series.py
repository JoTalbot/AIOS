"""Time Series Analysis for AIOS"""

import statistics
from typing import Dict, List


class TimeSeriesAnalyzer:
    """Basic time series analysis and forecasting."""

    def __init__(self):
        self.series: Dict[str, List[float]] = {}

    def add_data(self, series_name: str, value: float) -> None:
        """Execute add data."""
        if series_name not in self.series:
            self.series[series_name] = []
        self.series[series_name].append(value)
        if len(self.series[series_name]) > 1000:
            self.series[series_name] = self.series[series_name][-1000:]

    def moving_average(self, series_name: str, window: int = 5) -> List[float]:
        """Execute moving average."""
        data = self.series.get(series_name, [])
        if len(data) < window:
            return data
        return [sum(data[i : i + window]) / window for i in range(len(data) - window + 1)]

    def detect_trend(self, series_name: str) -> str:
        """Execute detect trend."""
        data = self.series.get(series_name, [])
        if len(data) < 3:
            return "insufficient_data"
        slope = (data[-1] - data[0]) / len(data)
        if slope > 0.1:
            return "increasing"
        elif slope < -0.1:
            return "decreasing"
        return "stable"

    def stats(self) -> dict:
        """Return statistics dict."""
        return {"series": len(self.series)}
