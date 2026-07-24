"""Digital Twin for AIOS v10.6.0.

Digital twin simulation with state management, configurable outcomes,
what-if analysis, state diffing, rollback, and event injection.

Classes:
    TwinProperty    — named property with value and type
    SimulationOutcome — result of a simulation action
    DigitalTwin     — enhanced twin with simulation, what-if, rollback
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ── Twin Property ────────────────────────────────────────────────────────────


@dataclass
class TwinProperty:
    """Named property with value and metadata."""

    name: str
    value: Any
    type: str = ""
    unit: str = ""
    min_value: float | None = None
    max_value: float | None = None

    def validate(self, new_value: Any) -> bool:
        """Validate new value against bounds."""
        if self.min_value is not None and isinstance(new_value, (int, float)):
            if new_value < self.min_value:
                return False
        if self.max_value is not None and isinstance(new_value, (int, float)):
            if new_value > self.max_value:
                return False
        return True


# ── Simulation Outcome ──────────────────────────────────────────────────────


@dataclass
class SimulationOutcome:
    """Result of a simulation action."""

    action: str
    predicted_outcome: str = "success"  # success, failure, degraded
    confidence: float = 0.8
    effects: dict[str, Any] = field(default_factory=dict)  # property changes
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)
    warnings: list[str] = field(default_factory=list)


# ── Digital Twin ─────────────────────────────────────────────────────────────


class DigitalTwin:
    """Enhanced digital twin with simulation, what-if analysis, and rollback.

    Features:
    - Property-based state management with validation
    - Action simulation with configurable outcomes
    - What-if analysis (simulate without committing)
    - State diffing (compare before/after)
    - State rollback (undo last sync)
    - Event injection for testing
    """

    def __init__(self, twin_id: str, real_entity: str) -> None:
        self.twin_id = twin_id
        self.real_entity = real_entity
        self.properties: dict[str, TwinProperty] = {}
        self.state: dict[str, Any] = {}
        self.history: list[dict[str, Any]] = []
        self._simulations: list[SimulationOutcome] = []
        self._action_handlers: dict[str, Callable] = {}

    # ── Property Management ─────────────────────────────────────

    def add_property(
        self,
        name: str,
        value: Any,
        type: str = "",
        unit: str = "",
        min_value: float | None = None,
        max_value: float | None = None,
    ) -> TwinProperty:
        """Add a property to the twin."""
        prop = TwinProperty(
            name=name,
            value=value,
            type=type,
            unit=unit,
            min_value=min_value,
            max_value=max_value,
        )
        self.properties[name] = prop
        self.state[name] = value
        return prop

    def update_property(self, name: str, value: Any) -> bool:
        """Update a property value. Returns False if validation fails."""
        prop = self.properties.get(name)
        if prop is None:
            self.state[name] = value
            return True
        if not prop.validate(value):
            logger.warning("Property '%s' value %s out of bounds", name, value)
            return False
        prop.value = value
        self.state[name] = value
        return True

    def get_property(self, name: str) -> Any:
        """Get property value."""
        prop = self.properties.get(name)
        return prop.value if prop else self.state.get(name)

    # ── State Sync ──────────────────────────────────────────────

    def sync(self, new_state: dict[str, Any]) -> dict[str, Any]:
        """Sync twin state with new data. Returns diff."""
        diff = self._compute_diff(self.state, new_state)
        self.history.append(
            {"state": self.state.copy(), "diff": diff, "timestamp": time.time()}
        )
        self.state.update(new_state)
        # Update properties
        for name, value in new_state.items():
            if name in self.properties:
                self.properties[name].value = value
        return diff

    def _compute_diff(self, old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
        """Compute diff between two states."""
        diff = {"added": {}, "removed": {}, "changed": {}}
        for key, value in new.items():
            if key not in old:
                diff["added"][key] = value
            elif old[key] != value:
                diff["changed"][key] = {"old": old[key], "new": value}
        for key, old_val in old.items():
            if key not in new:
                diff["removed"][key] = old_val
        return diff

    def rollback(self) -> dict[str, Any]:
        """Rollback to previous state."""
        if not self.history:
            return {}
        entry = self.history.pop()
        self.state = entry["state"]
        for name, value in self.state.items():
            if name in self.properties:
                self.properties[name].value = value
        return self.state

    def get_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return state history."""
        return self.history[-limit:]

    # ── Simulation ──────────────────────────────────────────────

    def register_action(
        self, name: str, handler: Callable[[dict[str, Any]], SimulationOutcome]
    ) -> None:
        """Register a simulation action handler."""
        self._action_handlers[name] = handler

    def simulate(self, action: str) -> SimulationOutcome:
        """Simulate an action and return predicted outcome.

        Uses registered handler or default logic.
        """
        handler = self._action_handlers.get(action)
        if handler:
            outcome = handler(self.state)
        else:
            # Default: predict success with moderate confidence
            outcome = SimulationOutcome(
                action=action,
                predicted_outcome="success",
                confidence=0.7,
            )
        self._simulations.append(outcome)
        return outcome

    def what_if(
        self, action: str, assumed_changes: dict[str, Any] | None = None
    ) -> SimulationOutcome:
        """What-if analysis: simulate without committing changes.

        Temporarily applies assumed_changes, runs simulation, then restores.
        """
        # Save current state
        saved_state = self.state.copy()

        # Apply assumed changes
        if assumed_changes:
            self.state.update(assumed_changes)

        # Simulate
        outcome = self.simulate(action)

        # Restore state (what-if = no commit)
        self.state = saved_state

        # Add what-if marker
        outcome.effects = assumed_changes or {}
        outcome.warnings.append("what-if: changes not committed")
        return outcome

    def apply_simulation(self, outcome: SimulationOutcome) -> bool:
        """Apply simulation outcome effects to twin state."""
        if outcome.effects:
            return self.sync(outcome.effects) is not None
        return True

    def inject_event(
        self, event_type: str, event_data: dict[str, Any]
    ) -> SimulationOutcome:
        """Inject an event for testing (e.g., failure, recovery)."""
        outcome = SimulationOutcome(
            action=f"inject_{event_type}",
            predicted_outcome="success" if event_type == "recovery" else "failure",
            confidence=1.0,
            effects=event_data,
        )
        self._simulations.append(outcome)
        return outcome

    # ── Queries ─────────────────────────────────────────────────

    def get_simulations(self, limit: int = 50) -> list[SimulationOutcome]:
        """Return simulation history."""
        return self._simulations[-limit:]

    def get_state(self) -> dict[str, Any]:
        """Return current state."""
        return self.state.copy()

    def compare_to(self, other_state: dict[str, Any]) -> dict[str, Any]:
        """Compare twin state to another state."""
        return self._compute_diff(self.state, other_state)

    # ── Stats ───────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        return {
            "id": self.twin_id,
            "entity": self.real_entity,
            "properties": len(self.properties),
            "history_length": len(self.history),
            "simulations": len(self._simulations),
            "state_keys": len(self.state),
        }
