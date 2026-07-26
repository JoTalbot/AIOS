from datetime import datetime, timedelta
from typing import Dict, List, Any
from collections import defaultdict

class AnalyticsEngine:
    def __init__(self, message_logs, metrics):
        self.logs = message_logs
        self.metrics = metrics

    def get_conversion_rate(self, days: int = 7) -> Dict[str, float]:
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent = [m for m in self.metrics if m.created_at > cutoff]
        created = sum(1 for m in recent if m.metric_type == "draft_created")
        approved = sum(1 for m in recent if m.metric_type == "draft_approved")
        rate = (approved / created * 100) if created > 0 else 0
        return {"period_days": days, "created": created, "approved": approved, "rate": round(rate, 2)}

    def get_avg_response_time(self, days: int = 7) -> float:
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent = [l for l in self.logs if l.created_at > cutoff and l.processing_time]
        if not recent:
            return 0.0
        return sum(l.processing_time for l in recent) / len(recent)

    def get_top_platforms(self, days: int = 30) -> List[Dict[str, Any]]:
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent = [l for l in self.logs if l.created_at > cutoff]
        counts = defaultdict(int)
        for log in recent:
            counts[log.platform] += 1
        return [{"platform": p, "count": c} for p, c in sorted(counts.items(), key=lambda x: x[1], reverse=True)]

    def get_intent_distribution(self, days: int = 7) -> Dict[str, int]:
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent = [l for l in self.logs if l.created_at > cutoff and l.intent]
        counts = defaultdict(int)
        for log in recent:
            counts[log.intent] += 1
        return dict(counts)

    def get_seasonal_patterns(self, days: int = 30) -> Dict[str, int]:
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent = [l for l in self.logs if l.created_at > cutoff]
        hourly = defaultdict(int)
        for log in recent:
            hourly[log.created_at.hour] += 1
        return {str(h): c for h, c in sorted(hourly.items())}

    def get_full_report(self) -> Dict[str, Any]:
        return {
            "conversion_7d": self.get_conversion_rate(7),
            "conversion_30d": self.get_conversion_rate(30),
            "avg_response_time_7d": round(self.get_avg_response_time(7), 2),
            "top_platforms_30d": self.get_top_platforms(30),
            "intent_distribution_7d": self.get_intent_distribution(7),
            "seasonal_patterns_30d": self.get_seasonal_patterns(30)
        }
