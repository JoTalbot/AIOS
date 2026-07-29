"""AIOS Android Auto-Study Orchestrator.

Automates app study workflows: launch, UI exploration, interaction recording,
and telemetry collection. Integrates with AndroidDriver, AndroidObservability,
and Telemetry for real-time dashboard metrics.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

from .android_driver import ADBDriver, AndroidDriver, UIContext
from .android_observability import AndroidExecutionEvent, AndroidObservability
from .telemetry import Telemetry
from .telemetry import telemetry as global_telemetry


class StudyPhase(StrEnum):
    """Auto-study execution phase."""
    DISCOVERY = "discovery"
    LAUNCH = "launch"
    EXPLORE = "explore"
    INTERACT = "interact"
    MEASURE = "measure"
    COMPLETE = "complete"
    FAILED = "failed"


class InteractionType(StrEnum):
    """Types of automated interactions."""
    TAP = "tap"
    SWIPE = "swipe"
    INPUT_TEXT = "input_text"
    BACK = "back"
    HOME = "home"
    SCROLL = "scroll"
    WAIT = "wait"


@dataclass
class StudyStep:
    """Single step in a study scenario."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    phase: StudyPhase = StudyPhase.DISCOVERY
    interaction: InteractionType = InteractionType.WAIT
    target: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    description: str = ""
    started_at: float | None = None
    completed_at: float | None = None
    success: bool = False
    latency_ms: float = 0.0
    error: str | None = None
    ui_context: UIContext | None = None


@dataclass
class StudyScenario:
    """Predefined study scenario for an app."""
    name: str
    package: str
    description: str
    steps: list[StudyStep] = field(default_factory=list)
    max_duration_sec: int = 300


@dataclass
class StudyResult:
    """Result of a completed study run."""
    study_id: str
    package: str
    scenario_name: str
    status: StudyPhase
    started_at: float
    completed_at: float | None
    steps_total: int
    steps_completed: int
    steps_failed: int
    avg_latency_ms: float
    total_events: int
    failure_rate: float
    screenshots: list[str] = field(default_factory=list)
    events: list[AndroidExecutionEvent] = field(default_factory=list)
    error: str | None = None


class AndroidAutoStudy:
    """Orchestrates automated Android app study sessions."""

    DEFAULT_SCENARIOS = {
        "basic_explore": StudyScenario(
            name="basic_explore",
            package="ua.slando",
            description="Launch app and capture initial UI hierarchy",
            steps=[
                StudyStep(phase=StudyPhase.LAUNCH, interaction=InteractionType.WAIT,
                          target="app_launch", description="Launch app and wait for main activity"),
                StudyStep(phase=StudyPhase.EXPLORE, interaction=InteractionType.WAIT,
                          target="ui_dump", description="Capture initial UI hierarchy"),
            ]
        ),
        "search_flow": StudyScenario(
            name="search_flow",
            package="ua.slando",
            description="Open search, enter query and submit",
            steps=[
                StudyStep(phase=StudyPhase.LAUNCH, interaction=InteractionType.WAIT,
                          target="app_launch", description="Launch app"),
                StudyStep(phase=StudyPhase.INTERACT, interaction=InteractionType.TAP,
                          target="search_button", params={"by_text": "Поиск"},
                          description="Open search"),
                StudyStep(phase=StudyPhase.INTERACT, interaction=InteractionType.INPUT_TEXT,
                          target="search_input", params={"text": "iPhone 15"},
                          description="Enter search query"),
                StudyStep(phase=StudyPhase.INTERACT, interaction=InteractionType.TAP,
                          target="search_submit", params={"by_text": "Найти"},
                          description="Submit search"),
            ]
        ),
        "listing_browse": StudyScenario(
            name="listing_browse",
            package="ua.slando",
            description="Open first listing and return back",
            steps=[
                StudyStep(phase=StudyPhase.LAUNCH, interaction=InteractionType.WAIT,
                          target="app_launch", description="Launch app"),
                StudyStep(phase=StudyPhase.INTERACT, interaction=InteractionType.TAP,
                          target="first_item", params={"index": 0},
                          description="Tap first listing"),
                StudyStep(phase=StudyPhase.EXPLORE, interaction=InteractionType.WAIT,
                          target="detail_screen", description="Wait for detail screen"),
                StudyStep(phase=StudyPhase.INTERACT, interaction=InteractionType.BACK,
                          target="back", description="Return to feed"),
            ]
        ),
        "chat_flow": StudyScenario(
            name="chat_flow",
            package="ua.slando",
            description="Open chat from first listing",
            steps=[
                StudyStep(phase=StudyPhase.LAUNCH, interaction=InteractionType.WAIT,
                          target="app_launch", description="Launch app"),
                StudyStep(phase=StudyPhase.INTERACT, interaction=InteractionType.TAP,
                          target="first_item", params={"index": 0},
                          description="Tap first listing"),
                StudyStep(phase=StudyPhase.INTERACT, interaction=InteractionType.TAP,
                          target="chat_button", params={"by_text": "Написать"},
                          description="Open chat"),
                StudyStep(phase=StudyPhase.EXPLORE, interaction=InteractionType.WAIT,
                          target="chat_screen", description="Wait for chat screen"),
            ]
        ),
        "profile_check": StudyScenario(
            name="profile_check",
            package="ua.slando",
            description="Open profile/settings and return",
            steps=[
                StudyStep(phase=StudyPhase.LAUNCH, interaction=InteractionType.WAIT,
                          target="app_launch", description="Launch app"),
                StudyStep(phase=StudyPhase.INTERACT, interaction=InteractionType.TAP,
                          target="profile", params={"by_text": "Профиль"},
                          description="Open profile"),
                StudyStep(phase=StudyPhase.EXPLORE, interaction=InteractionType.WAIT,
                          target="profile_screen", description="Wait for profile screen"),
                StudyStep(phase=StudyPhase.INTERACT, interaction=InteractionType.BACK,
                          target="back", description="Return to previous screen"),
            ]
        ),
    }

    def __init__(
        self,
        device_id: str = "emulator-5554",
        driver: AndroidDriver | None = None,
        observability: AndroidObservability | None = None,
        telemetry: Telemetry | None = None,
    ):
        self.device_id = device_id
        self.driver = driver or ADBDriver(device_id=device_id)
        self.observability = observability or AndroidObservability(device_id)
        self.telemetry = telemetry or global_telemetry
        self.current_study: StudyResult | None = None
        self._running = False
        self._cancel_requested = False

    async def run_study(
        self,
        package: str,
        scenario_name: str = "basic_explore",
        custom_steps: list[StudyStep] | None = None,
        max_duration_sec: int = 300,
    ) -> StudyResult:
        """Execute a complete auto-study scenario."""
        self._running = True
        self._cancel_requested = False

        scenario = self.DEFAULT_SCENARIOS.get(scenario_name)
        if not scenario:
            raise ValueError(f"Unknown scenario: {scenario_name}")

        if custom_steps:
            scenario = StudyScenario(
                name=f"custom_{scenario_name}",
                package=package,
                description=f"Custom: {scenario_name}",
                steps=custom_steps,
                max_duration_sec=max_duration_sec,
            )
        else:
            scenario = StudyScenario(
                name=scenario.name,
                package=package,
                description=scenario.description,
                steps=[s for s in scenario.steps],
                max_duration_sec=max_duration_sec,
            )

        study_id = uuid.uuid4().hex[:12]
        started_at = time.time()

        self.current_study = StudyResult(
            study_id=study_id,
            package=package,
            scenario_name=scenario.name,
            status=StudyPhase.DISCOVERY,
            started_at=started_at,
            completed_at=None,
            steps_total=len(scenario.steps),
            steps_completed=0,
            steps_failed=0,
            avg_latency_ms=0.0,
            total_events=0,
            failure_rate=0.0,
        )

        screenshots = []
        events = []
        latencies = []

        try:
            self.telemetry.increment_counter("android_study_started", 1.0)
            self.telemetry.set_gauge("android_study_active", 1.0)

            if hasattr(self.driver, "capabilities") and hasattr(self.driver.capabilities, "package"):
                self.driver.capabilities.package = package

            if not self.driver.launch_app():
                raise RuntimeError(f"Failed to launch {package}")

            for i, step in enumerate(scenario.steps):
                if self._cancel_requested:
                    raise asyncio.CancelledError("Study cancelled by user")

                step.started_at = time.time()
                self.current_study.status = step.phase

                await self._execute_step(step, package)

                step.completed_at = time.time()
                step.latency_ms = (step.completed_at - step.started_at) * 1000
                latencies.append(step.latency_ms)

                if step.success:
                    self.current_study.steps_completed += 1
                else:
                    self.current_study.steps_failed += 1

                if step.ui_context and step.ui_context.screenshot_path:
                    screenshots.append(step.ui_context.screenshot_path)

                if step.error:
                    self.telemetry.increment_counter("android_study_step_failed", 1.0)

            self.current_study.status = StudyPhase.COMPLETE
            self.current_study.screenshots = screenshots
            self.current_study.events = self.observability.events.copy()

        except asyncio.CancelledError:
            self.current_study.status = StudyPhase.FAILED
            self.current_study.error = "Cancelled by user"
        except Exception as e:
            if not self.current_study:
                self.current_study = StudyResult(
                    study_id=uuid.uuid4().hex[:12],
                    package=package,
                    scenario_name=scenario.name,
                    status=StudyPhase.FAILED,
                    started_at=started_at,
                    completed_at=None,
                    steps_total=len(scenario.steps),
                    steps_completed=0,
                    steps_failed=1,
                    avg_latency_ms=0.0,
                    total_events=0,
                    failure_rate=1.0,
                    error=str(e),
                )
            else:
                self.current_study.status = StudyPhase.FAILED
                self.current_study.error = str(e)
            self.telemetry.increment_counter("android_study_error", 1.0)
        finally:
            completed_at = time.time()
            self.current_study.completed_at = completed_at
            self.current_study.avg_latency_ms = sum(latencies) / len(latencies) if latencies else 0
            self.current_study.total_events = len(self.observability.events)
            self.current_study.failure_rate = self.observability.failure_rate()

            self.telemetry.set_gauge("android_study_active", 0.0)
            self.telemetry.record_metric("android_study_duration_sec", completed_at - started_at)
            self.telemetry.record_metric("android_study_steps_completed", self.current_study.steps_completed)
            self.telemetry.record_metric("android_study_failure_rate", self.current_study.failure_rate)

            self._running = False

        return self.current_study

    async def _execute_step(self, step: StudyStep, package: str) -> None:
        """Execute a single study step."""
        try:
            if step.interaction == InteractionType.WAIT:
                await asyncio.sleep(step.params.get("duration", 2.0))
                step.ui_context = self.driver.dump_ui()
                step.success = True

            elif step.interaction == InteractionType.TAP:
                if "by_text" in step.params:
                    ui = self.driver.dump_ui()
                    # Find element by text in XML
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(ui.xml)
                    for elem in root.iter("node"):
                        if step.params["by_text"] in (elem.get("text", "") or ""):
                            bounds = elem.get("bounds", "")
                            if bounds:
                                coords = self._parse_bounds(bounds)
                                self.driver.tap(coords[0], coords[1])
                                step.success = True
                                break
                elif "x" in step.params and "y" in step.params:
                    self.driver.tap(step.params["x"], step.params["y"])
                    step.success = True
                await asyncio.sleep(1.0)
                step.ui_context = self.driver.dump_ui()

            elif step.interaction == InteractionType.SWIPE:
                x1 = step.params.get("x1", 500)
                y1 = step.params.get("y1", 1000)
                x2 = step.params.get("x2", 500)
                y2 = step.params.get("y2", 200)
                duration = step.params.get("duration", 300)
                self.driver.swipe(x1, y1, x2, y2, duration)
                await asyncio.sleep(0.5)
                step.ui_context = self.driver.dump_ui()
                step.success = True

            elif step.interaction == InteractionType.INPUT_TEXT:
                text = step.params.get("text", "")
                self.driver.input_text(text)
                await asyncio.sleep(0.5)
                step.ui_context = self.driver.dump_ui()
                step.success = True

            elif step.interaction == InteractionType.BACK:
                self.driver.back()
                await asyncio.sleep(0.5)
                step.ui_context = self.driver.dump_ui()
                step.success = True

            elif step.interaction == InteractionType.HOME:
                self.driver.home()
                await asyncio.sleep(1.0)
                step.ui_context = self.driver.dump_ui()
                step.success = True

            else:
                step.success = True

            self.observability.record(
                package=package,
                action=step.interaction.value,
                latency_ms=step.latency_ms,
                success=step.success,
                screen=step.ui_context.current_activity if step.ui_context else None,
                meta={"step_id": step.id, "target": step.target},
            )

        except Exception as e:
            step.success = False
            step.error = str(e)
            self.observability.record(
                package=package,
                action=step.interaction.value,
                latency_ms=step.latency_ms,
                success=False,
                meta={"step_id": step.id, "target": step.target, "error": str(e)},
            )

    def _parse_bounds(self, bounds: str) -> tuple[int, int]:
        """Parse Android bounds string '[x1,y1][x2,y2]' -> center point."""
        import re
        match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds)
        if match:
            x1, y1, x2, y2 = map(int, match.groups())
            return ((x1 + x2) // 2, (y1 + y2) // 2)
        return (500, 1000)

    def cancel(self) -> None:
        """Request cancellation of current study."""
        self._cancel_requested = True

    def get_status(self) -> dict[str, Any]:
        """Get current study status for dashboard."""
        if not self.current_study:
            return {"active": False}

        return {
            "active": self._running,
            "study_id": self.current_study.study_id,
            "package": self.current_study.package,
            "scenario": self.current_study.scenario_name,
            "status": self.current_study.status.value,
            "progress": f"{self.current_study.steps_completed}/{self.current_study.steps_total}",
            "steps_completed": self.current_study.steps_completed,
            "steps_failed": self.current_study.steps_failed,
            "avg_latency_ms": round(self.current_study.avg_latency_ms, 1),
            "failure_rate": round(self.current_study.failure_rate, 3),
            "events_count": len(self.observability.events),
            "failure_risk": round(self.observability.predict_failure_risk(), 3),
        }

    def get_scenarios(self) -> dict[str, dict]:
        """Get available study scenarios."""
        return {
            name: {
                "name": s.name,
                "package": s.package,
                "description": s.description,
                "steps": len(s.steps),
                "max_duration_sec": s.max_duration_sec,
            }
            for name, s in self.DEFAULT_SCENARIOS.items()
        }


async def run_auto_study(
    package: str = "ua.slando",
    scenario: str = "basic_explore",
    device_id: str = "emulator-5554",
) -> StudyResult:
    """Convenience function to run a study from CLI or scheduler."""
    study = AndroidAutoStudy(device_id=device_id)
    return await study.run_study(package, scenario)


if __name__ == "__main__":
    import sys
    pkg = sys.argv[1] if len(sys.argv) > 1 else "ua.slando"
    scn = sys.argv[2] if len(sys.argv) > 2 else "basic_explore"
    result = asyncio.run(run_auto_study(pkg, scn))
    print(json.dumps(asdict(result), default=str, indent=2))