"""Metrics Collector — сбор статистики работы AI Advisor."""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

class MetricsCollector:
    def __init__(self, storage_path: str = "data/metrics"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.current_date = datetime.utcnow().strftime("%Y-%m-%d")
        self.metrics_file = self.storage_path / f"{self.current_date}.json"
        self._load()

    def _load(self):
        if self.metrics_file.exists():
            self.data = json.loads(self.metrics_file.read_text())
        else:
            self.data = {
                "date": self.current_date,
                "drafts_created": 0,
                "drafts_approved": 0,
                "drafts_rejected": 0,
                "escalations": 0,
                "compliance_violations": 0,
                "intents": {},
                "sentiments": {"positive": 0, "neutral": 0, "negative": 0},
                "platforms": {}
            }

    def _save(self):
        self.metrics_file.write_text(json.dumps(self.data, indent=2))

    def record_draft_created(self):
        self.data["drafts_created"] += 1
        self._save()

    def record_draft_approved(self):
        self.data["drafts_approved"] += 1
        self._save()

    def record_draft_rejected(self):
        self.data["drafts_rejected"] += 1
        self._save()

    def record_escalation(self):
        self.data["escalations"] += 1
        self._save()

    def record_compliance_violation(self):
        self.data["compliance_violations"] += 1
        self._save()

    def record_intent(self, intent: str):
        self.data["intents"][intent] = self.data["intents"].get(intent, 0) + 1
        self._save()

    def record_sentiment(self, sentiment: str):
        self.data["sentiments"][sentiment] = self.data["sentiments"].get(sentiment, 0) + 1
        self._save()

    def record_platform(self, platform: str):
        self.data["platforms"][platform] = self.data["platforms"].get(platform, 0) + 1
        self._save()

    def get_summary(self) -> Dict[str, Any]:
        total_drafts = self.data["drafts_created"]
        approval_rate = (self.data["drafts_approved"] / total_drafts * 100) if total_drafts > 0 else 0
        return {
            "date": self.data["date"],
            "drafts_created": total_drafts,
            "approval_rate": f"{approval_rate:.1f}%",
            "escalations": self.data["escalations"],
            "compliance_violations": self.data["compliance_violations"],
            "top_intents": sorted(self.data["intents"].items(), key=lambda x: x[1], reverse=True)[:5],
            "sentiment_distribution": self.data["sentiments"]
        }
