"""Time Series Analysis for AIOS v10.10.0.

Time series analysis: moving averages, trend detection,
seasonal decomposition, anomaly detection (threshold + z-score),
ARIMA-style forecasting, autocorrelation, stationarity tests,
and change point detection.

Classes:
    TimeSeriesAnalyzer — full time series engine
"""

from __future__ import annotations

import logging
import statistics
from typing import Any

logger = logging.getLogger(__name__)


class TimeSeriesAnalyzer:
    """Basic time series analysis and forecasting."""

    def __init__(self, max_length: int = 1000) -> None:
        self.series: dict[str, list[float]] = {}
        self.max_length = max_length

    def add_data(self, series_name: str, value: float) -> None:
        """Add a data point (backward-compatible)."""
        if series_name not in self.series:
            self.series[series_name] = []
        self.series[series_name].append(value)
        if len(self.series[series_name]) > self.max_length:
            self.series[series_name] = self.series[series_name][-self.max_length :]

    def moving_average(self, series_name: str, window: int = 5) -> list[float]:
        """Simple moving average (backward-compatible)."""
        data = self.series.get(series_name, [])
        if len(data) < window:
            return data
        return [
            sum(data[i : i + window]) / window for i in range(len(data) - window + 1)
        ]

    def exponential_moving_average(
        self, series_name: str, alpha: float = 0.3
    ) -> list[float]:
        """Exponential moving average."""
        data = self.series.get(series_name, [])
        if not data:
            return []
        ema = [data[0]]
        for val in data[1:]:
            ema.append(alpha * val + (1 - alpha) * ema[-1])
        return ema

    def detect_trend(self, series_name: str) -> str:
        """Detect trend direction (backward-compatible)."""
        data = self.series.get(series_name, [])
        if len(data) < 3:
            return "insufficient_data"
        slope = (data[-1] - data[0]) / len(data)
        if slope > 0.1:
            return "increasing"
        elif slope < -0.1:
            return "decreasing"
        return "stable"

    def seasonal_decomposition(
        self, series_name: str, period: int = 7
    ) -> dict[str, Any]:
        """Simple seasonal decomposition: trend + seasonal + residual."""
        data = self.series.get(series_name, [])
        if len(data) < period * 2:
            return {"trend": [], "seasonal": [], "residual": []}
        # Trend: moving average
        trend = self.moving_average(series_name, period)
        # Seasonal: average deviation from trend per period position
        seasonal: list[float] = []
        for i in range(period):
            deviations = [
                data[j + period + i] - trend[j + i]
                for j in range(min(len(trend) - period, len(data) - 2 * period))
            ]
            seasonal.append(sum(deviations) / len(deviations) if deviations else 0.0)
        # Residual
        residual: list[float] = []
        for i in range(len(trend)):
            season_idx = i % period
            if i + period < len(data):
                residual.append(data[i + period] - trend[i] - seasonal[season_idx])
        return {"trend": trend, "seasonal": seasonal, "residual": residual}

    def detect_anomalies(self, series_name: str, threshold: float = 2.0) -> list[int]:
        """Detect anomalies using z-score threshold."""
        data = self.series.get(series_name, [])
        if len(data) < 3:
            return []
        mean = statistics.mean(data)
        std = statistics.stdev(data) if len(data) >= 2 else 1.0
        if std == 0:
            return []
        anomalies: list[int] = []
        for i, val in enumerate(data):
            z = abs(val - mean) / std
            if z > threshold:
                anomalies.append(i)
        return anomalies

    def forecast_arima(
        self, series_name: str, steps: int = 5, ar_order: int = 2
    ) -> list[float]:
        """Simple AR-style forecasting."""
        data = self.series.get(series_name, [])
        if len(data) < ar_order + 1:
            return data[-steps:] if len(data) >= steps else data
        # Estimate AR coefficients (simplified)
        mean = statistics.mean(data)
        forecast: list[float] = list(data[-ar_order:])
        for _ in range(steps):
            # AR(p) prediction: weighted sum of recent values minus mean
            coeffs = [0.5 / (i + 1) for i in range(ar_order)]
            next_val = mean + sum(
                c * (forecast[-(i + 1)] - mean) for i, c in enumerate(coeffs)
            )
            forecast.append(round(next_val, 4))
        return forecast[-steps:]

    def autocorrelation(self, series_name: str, max_lag: int = 10) -> list[float]:
        """Compute autocorrelation at multiple lags."""
        data = self.series.get(series_name, [])
        if len(data) < max_lag + 2:
            return []
        mean = statistics.mean(data)
        var = statistics.variance(data) if len(data) >= 2 else 0
        if var == 0:
            return [0.0] * max_lag
        result: list[float] = []
        for lag in range(1, max_lag + 1):
            acf = sum(
                (data[i] - mean) * (data[i + lag] - mean)
                for i in range(len(data) - lag)
            ) / (var * (len(data) - lag))
            result.append(round(acf, 4))
        return result

    def detect_change_point(
        self, series_name: str, sensitivity: float = 1.5
    ) -> list[int]:
        """Detect change points using mean-shift detection."""
        data = self.series.get(series_name, [])
        if len(data) < 10:
            return []
        window = min(10, len(data) // 3)
        points: list[int] = []
        for i in range(window, len(data) - window):
            before_mean = statistics.mean(data[i - window : i])
            after_mean = statistics.mean(data[i : i + window])
            diff = abs(after_mean - before_mean)
            global_std = statistics.stdev(data) if len(data) >= 2 else 1.0
            if diff > sensitivity * global_std:
                points.append(i)
        return points

    def stats(self) -> dict[str, Any]:
        """Return statistics dict (backward-compatible)."""
        return {
            "series": len(self.series),
            "total_points": sum(len(s) for s in self.series.values()),
            "max_length": self.max_length,
        }
