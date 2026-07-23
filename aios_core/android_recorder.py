"""AIOS Android Appium Scenario Recorder (M2).

Records and replays touchscreen/type sequences for regression and reuse.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RecordedStep:
    action: str
    ts: float
    meta: Dict[str, Any] = field(default_factory=dict)


class ScenarioRecorder:
    def __init__(
        self,
        package: str,
        device_id: str,
        path: str = "/tmp/aios_android_scenario.json",
    ):
        self.package = package
        self.device_id = device_id
        self.path = path
        self.steps: List[RecordedStep] = []

    def record(self, action: str, meta: Optional[Dict[str, Any]] = None):
        self.steps.append(RecordedStep(action=action, ts=time.time(), meta=meta or {}))

    def save(self):
        payload = {
            "package": self.package,
            "device_id": self.device_id,
            "steps": [asdict(step) for step in self.steps],
        }
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
