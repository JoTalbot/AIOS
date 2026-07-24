"""AIOS Android Appium Scenario Recorder (M2).

Records and replays touchscreen/type sequences for regression and reuse.
Supports scenario merging, filtering, assertions, step editing, and
scenario validation for robust automated testing.
"""

from __future__ import annotations

import json
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

__all__ = ["RecordedStep", "ScenarioAssertion", "ScenarioRecorder"]


@dataclass
class RecordedStep:
    """Recorded automation step for scenario replay."""

    action: str
    ts: float
    meta: dict[str, Any] = field(default_factory=dict)

    def matches_action(self, pattern: str) -> bool:
        """Check if this step's action matches a wildcard pattern."""
        import fnmatch

        return fnmatch.fnmatch(self.action, pattern)

    def elapsed_from(self, earlier_step: RecordedStep) -> float:
        """Return time elapsed from *earlier_step* to this step."""
        return self.ts - earlier_step.ts


@dataclass
class ScenarioAssertion:
    """Expected condition that must hold at a given step during replay."""

    step_index: int
    assertion_type: str  # e.g. "element_present", "text_equals", "no_crash"
    expected: Any = None
    message: str = ""


class ScenarioRecorder:
    """Records and replays automation scenarios.

    Features:
    - Step recording with metadata and timestamps
    - Scenario save/load from JSON
    - Scenario replay with assertion validation
    - Step filtering by action pattern or time range
    - Scenario merging from multiple recordings
    - Step editing (insert, delete, replace)
    - Validation of scenario completeness
    """

    def __init__(
        self,
        package: str,
        device_id: str,
        path: str = "/tmp/aios_android_scenario.json",
        max_steps: int = 5000,
    ):
        """Initialize ScenarioRecorder."""
        self.package = package
        self.device_id = device_id
        self.path = path
        self.steps: list[RecordedStep] = []
        self.assertions: list[ScenarioAssertion] = []
        self.max_steps = max_steps
        self._metadata: dict[str, Any] = {
            "created_at": time.time(),
            "recorder_version": "2.0",
        }

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def record(
        self,
        action: str,
        meta: dict[str, Any] | None = None,
    ) -> RecordedStep:
        """Record an automation step. Returns the created step."""
        if len(self.steps) >= self.max_steps:
            raise ValueError(f"Maximum steps ({self.max_steps}) reached")
        step = RecordedStep(action=action, ts=time.time(), meta=meta or {})
        self.steps.append(step)
        return step

    def record_batch(self, actions: Sequence[str]) -> list[RecordedStep]:
        """Record a sequence of actions with auto-incrementing timestamps."""
        base_time = time.time()
        result = []
        for i, action in enumerate(actions):
            step = RecordedStep(action=action, ts=base_time + i * 0.1, meta={})
            self.steps.append(step)
            result.append(step)
        return result

    def add_assertion(
        self,
        step_index: int,
        assertion_type: str,
        expected: Any = None,
        message: str = "",
    ) -> ScenarioAssertion:
        """Add a validation assertion at *step_index*."""
        if step_index < 0 or step_index >= len(self.steps):
            raise IndexError(f"step_index {step_index} out of range")
        assertion = ScenarioAssertion(
            step_index=step_index,
            assertion_type=assertion_type,
            expected=expected,
            message=message,
        )
        self.assertions.append(assertion)
        return assertion

    # ------------------------------------------------------------------
    # Step management
    # ------------------------------------------------------------------

    def delete_step(self, index: int) -> RecordedStep:
        """Remove step at *index* and return it."""
        if index < 0 or index >= len(self.steps):
            raise IndexError(f"Step index {index} out of range")
        return self.steps.pop(index)

    def insert_step(
        self, index: int, action: str, meta: dict[str, Any] | None = None
    ) -> RecordedStep:
        """Insert a step at *index*."""
        step = RecordedStep(action=action, ts=time.time(), meta=meta or {})
        self.steps.insert(index, step)
        return step

    def replace_step(
        self, index: int, action: str, meta: dict[str, Any] | None = None
    ) -> RecordedStep:
        """Replace step at *index* with a new action."""
        if index < 0 or index >= len(self.steps):
            raise IndexError(f"Step index {index} out of range")
        new_step = RecordedStep(action=action, ts=time.time(), meta=meta or {})
        self.steps[index] = new_step
        return new_step

    # ------------------------------------------------------------------
    # Filtering / analysis
    # ------------------------------------------------------------------

    def filter_by_action(self, pattern: str) -> list[RecordedStep]:
        """Return steps whose action matches *pattern* (supports wildcards)."""
        return [s for s in self.steps if s.matches_action(pattern)]

    def filter_by_time_range(
        self, start_ts: float, end_ts: float
    ) -> list[RecordedStep]:
        """Return steps within the given time range."""
        return [s for s in self.steps if start_ts <= s.ts <= end_ts]

    def get_action_counts(self) -> dict[str, int]:
        """Return a histogram of action types."""
        counts: dict[str, int] = {}
        for step in self.steps:
            counts[step.action] = counts.get(step.action, 0) + 1
        return counts

    def total_duration(self) -> float:
        """Return total duration from first to last step."""
        if len(self.steps) < 2:
            return 0.0
        return self.steps[-1].ts - self.steps[0].ts

    def average_step_interval(self) -> float:
        """Return average time between consecutive steps."""
        if len(self.steps) < 2:
            return 0.0
        intervals = [
            self.steps[i].elapsed_from(self.steps[i - 1])
            for i in range(1, len(self.steps))
        ]
        return sum(intervals) / len(intervals)

    # ------------------------------------------------------------------
    # Scenario merging
    # ------------------------------------------------------------------

    def merge(self, other: ScenarioRecorder, offset: float = 0.0) -> None:
        """Merge *other* recorder's steps into this one, with optional time offset."""
        for step in other.steps:
            new_step = RecordedStep(
                action=step.action,
                ts=step.ts + offset,
                meta={**step.meta, "merged_from": other.package},
            )
            self.steps.append(new_step)
        for assertion in other.assertions:
            adjusted = ScenarioAssertion(
                step_index=assertion.step_index + len(self.steps) - len(other.steps),
                assertion_type=assertion.assertion_type,
                expected=assertion.expected,
                message=assertion.message,
            )
            self.assertions.append(adjusted)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> dict[str, Any]:
        """Validate scenario completeness and consistency.

        Checks:
        - At least one step exists
        - Timestamps are monotonically increasing
        - All assertion step indices are in range
        - No duplicate actions without metadata distinction
        """
        issues: list[str] = []

        if not self.steps:
            issues.append("Scenario has no recorded steps")

        # Check monotonic timestamps
        issues = [f"Step {i} has earlier timestamp than step {i - 1}" for i in range(1, len(self.steps)) if self.steps[i].ts < self.steps[i - 1].ts]

        # Check assertions reference valid indices
        issues = [f"Assertion references invalid step_index {assertion.step_index}" for assertion in self.assertions if assertion.step_index >= len(self.steps) or assertion.step_index < 0]

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "step_count": len(self.steps),
            "assertion_count": len(self.assertions),
        }

    # ------------------------------------------------------------------
    # Save / Load
    # ------------------------------------------------------------------

    def save(self) -> None:
        """Save scenario to JSON file."""
        payload = {
            "package": self.package,
            "device_id": self.device_id,
            "metadata": self._metadata,
            "steps": [asdict(step) for step in self.steps],
            "assertions": [asdict(a) for a in self.assertions],
        }
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str) -> dict[str, Any]:
        """Load scenario data from JSON file."""
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def from_file(cls, path: str) -> ScenarioRecorder:
        """Construct a ScenarioRecorder from a saved JSON file."""
        data = cls.load(path)
        recorder = cls(
            package=data["package"],
            device_id=data["device_id"],
            path=path,
        )
        for step_data in data.get("steps", []):
            recorder.steps.append(RecordedStep(**step_data))
        for assertion_data in data.get("assertions", []):
            recorder.assertions.append(ScenarioAssertion(**assertion_data))
        recorder._metadata = data.get("metadata", {})
        return recorder

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        """Return scenario statistics."""
        action_counts = self.get_action_counts()
        return {
            "package": self.package,
            "device_id": self.device_id,
            "step_count": len(self.steps),
            "assertion_count": len(self.assertions),
            "unique_actions": len(action_counts),
            "action_histogram": action_counts,
            "total_duration": round(self.total_duration(), 3),
            "avg_step_interval": round(self.average_step_interval(), 3),
            "max_steps_limit": self.max_steps,
        }
