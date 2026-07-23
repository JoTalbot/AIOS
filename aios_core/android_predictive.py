"""AIOS Android M8 - Predictive Maintenance & Failure Prediction

Enhances M7 observability with predictive capabilities:
- Failure trend analysis
- Anomaly forecasting
- Self-healing recommendations
- Resource exhaustion prediction
"""

from __future__ import annotations

import time
import statistics
from collections import deque, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FailurePrediction:
    device_id: str
    risk_level: RiskLevel
    risk_score: float  # 0.0 - 1.0
    predicted_failure_in: Optional[float]  # seconds until likely failure
    reasons: List[str]
    recommendations: List[str]
    metrics_snapshot: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)


@dataclass
class TrendPoint:
    timestamp: float
    value: float
    label: str = ""


class PredictiveMaintenance:
    """M8 predictive engine - analyzes observability events to forecast failures."""

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self._failure_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self._latency_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self._success_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=window_size))
        self._predictions: List[FailurePrediction] = []
        self.version = "8.0.0"

    def record_event(self, device_id: str, action: str, latency_ms: float, success: bool):
        """Record execution event for trend analysis."""
        ts = time.time()
        self._latency_history[f"{device_id}:{action}"].append(TrendPoint(ts, latency_ms, action))
        self._success_history[f"{device_id}:{action}"].append(
            TrendPoint(ts, 1.0 if success else 0.0, action)
        )
        if not success:
            self._failure_history[device_id].append(TrendPoint(ts, 1.0, action))

    def _calculate_failure_rate_trend(self, device_id: str) -> Tuple[float, float, str]:
        """Returns (current_rate, trend_slope, description)."""
        failures = list(self._failure_history.get(device_id, []))
        if len(failures) < 3:
            return 0.0, 0.0, "insufficient data"

        # rate in last 5 min vs previous 5 min
        now = time.time()
        recent = [f for f in failures if now - f.timestamp < 300]
        older = [f for f in failures if 300 <= now - f.timestamp < 600]

        recent_rate = len(recent) / 5.0  # failures per minute
        older_rate = len(older) / 5.0

        trend = recent_rate - older_rate
        if trend > 0.5:
            desc = f"failure rate increasing: {older_rate:.2f} -> {recent_rate:.2f}/min"
        elif recent_rate > 1.0:
            desc = f"high steady failure rate: {recent_rate:.2f}/min"
        else:
            desc = f"stable low rate: {recent_rate:.2f}/min"

        return recent_rate, trend, desc

    def _calculate_latency_trend(
        self, device_id: str, action: str = ""
    ) -> Tuple[float, float, str]:
        """Latency trend analysis."""
        key = f"{device_id}:{action}" if action else device_id
        # gather all latencies for device
        points = []
        if action:
            points = list(self._latency_history.get(key, []))
        else:
            for k, dq in self._latency_history.items():
                if k.startswith(f"{device_id}:"):
                    points.extend(list(dq))

        if len(points) < 5:
            return 0.0, 0.0, "insufficient data"

        values = [p.value for p in points[-20:]]
        avg = statistics.mean(values)
        try:
            stdev = statistics.stdev(values) if len(values) > 1 else 0
        except:
            stdev = 0

        # simple linear regression slope for last 20 points
        if len(values) >= 10:
            x = list(range(len(values)))
            n = len(values)
            sum_x = sum(x)
            sum_y = sum(values)
            sum_xy = sum(a * b for a, b in zip(x, values))
            sum_xx = sum(a * a for a in x)
            denom = n * sum_xx - sum_x * sum_x
            slope = (n * sum_xy - sum_x * sum_y) / denom if denom != 0 else 0
        else:
            slope = 0

        if slope > 50:  # ms per step increasing
            desc = f"latency degrading: +{slope:.1f}ms/step, avg {avg:.0f}ms"
        elif avg > 5000:
            desc = f"high latency: {avg:.0f}ms avg, stdev {stdev:.0f}"
        else:
            desc = f"latency stable: {avg:.0f}ms avg"

        return avg, slope, desc

    def predict(self, device_id: str) -> FailurePrediction:
        """Generate failure prediction for device."""
        failure_rate, failure_trend, failure_desc = self._calculate_failure_rate_trend(device_id)
        latency_avg, latency_trend, latency_desc = self._calculate_latency_trend(device_id)

        reasons = []
        recommendations = []
        risk_score = 0.0

        # Analyze failure rate
        if failure_rate > 2.0:
            reasons.append(f"Критический уровень ошибок: {failure_desc}")
            risk_score += 0.4
            recommendations.append("Перезапустить эмулятор / почистить кэш uiautomator")
        elif failure_rate > 0.5:
            reasons.append(f"Повышенный уровень ошибок: {failure_desc}")
            risk_score += 0.2
            recommendations.append("Проверить стабильность ADB соединения")

        if failure_trend > 0.5:
            reasons.append(f"Тренд ухудшения: ошибки растут ({failure_trend:.2f})")
            risk_score += 0.2
            recommendations.append("Включить self-healing локаторы, увеличить retry")

        # Analyze latency
        if latency_avg > 8000:
            reasons.append(f"Критическая задержка: {latency_desc}")
            risk_score += 0.3
            recommendations.append("Эмулятор перегружен — уменьшить параллелизм, освободить RAM")
        elif latency_avg > 3000:
            reasons.append(f"Высокая задержка: {latency_desc}")
            risk_score += 0.15

        if latency_trend > 100:
            reasons.append(f"Деградация производительности: {latency_desc}")
            risk_score += 0.15
            recommendations.append("Профилировать tap/type операции, включить кэширование UI dump")

        # Success rate check
        success_points = []
        for k, dq in self._success_history.items():
            if k.startswith(f"{device_id}:"):
                success_points.extend(list(dq)[-50:])
        if success_points:
            success_rate = sum(p.value for p in success_points) / len(success_points)
            if success_rate < 0.5:
                reasons.append(f"Низкий success rate: {success_rate*100:.0f}%")
                risk_score += 0.3
                recommendations.append("Проверить селекторы, обновить hints в platforms/*.yaml")
            elif success_rate < 0.8:
                reasons.append(f"Средний success rate: {success_rate*100:.0f}%")
                risk_score += 0.1

        # Determine risk level
        risk_score = min(risk_score, 1.0)
        if risk_score >= 0.7:
            level = RiskLevel.CRITICAL
            predicted_in = 60  # 1 min
        elif risk_score >= 0.5:
            level = RiskLevel.HIGH
            predicted_in = 300  # 5 min
        elif risk_score >= 0.3:
            level = RiskLevel.MEDIUM
            predicted_in = 900  # 15 min
        else:
            level = RiskLevel.LOW
            predicted_in = None

        if not reasons:
            reasons.append("Система стабильна, аномалий не обнаружено")
            recommendations.append("Продолжать мониторинг")

        pred = FailurePrediction(
            device_id=device_id,
            risk_level=level,
            risk_score=risk_score,
            predicted_failure_in=predicted_in,
            reasons=reasons,
            recommendations=recommendations,
            metrics_snapshot={
                "failure_rate": failure_rate,
                "failure_trend": failure_trend,
                "latency_avg": latency_avg,
                "latency_trend": latency_trend,
                "failure_desc": failure_desc,
                "latency_desc": latency_desc,
            },
        )
        self._predictions.append(pred)
        if len(self._predictions) > 1000:
            self._predictions = self._predictions[-1000:]
        return pred

    def predict_all_devices(self) -> List[FailurePrediction]:
        """Predict for all known devices."""
        devices = set()
        for k in list(self._latency_history.keys()) + list(self._failure_history.keys()):
            if ":" in k:
                devices.add(k.split(":")[0])
            else:
                devices.add(k)
        return [self.predict(d) for d in devices]

    def get_recommendations(self, device_id: str) -> List[str]:
        pred = self.predict(device_id)
        return pred.recommendations

    def health_report(self) -> Dict[str, Any]:
        """Overall health report for fleet."""
        preds = self.predict_all_devices()
        critical = [p for p in preds if p.risk_level == RiskLevel.CRITICAL]
        high = [p for p in preds if p.risk_level == RiskLevel.HIGH]
        return {
            "total_devices": len(preds),
            "critical": len(critical),
            "high": len(high),
            "critical_devices": [p.device_id for p in critical],
            "avg_risk": sum(p.risk_score for p in preds) / len(preds) if preds else 0,
            "predictions": [
                {
                    "device": p.device_id,
                    "risk": p.risk_level.value,
                    "score": round(p.risk_score, 2),
                    "reasons": p.reasons[:2],
                    "eta": p.predicted_failure_in,
                }
                for p in preds
            ],
            "timestamp": time.time(),
            "version": self.version,
        }
