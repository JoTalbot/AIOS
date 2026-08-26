"""Compatibility facade for the new AIOS supervision lifecycle.

The runtime layer keeps its legacy recovery analytics API, while the actual
failure -> recovery -> persistence lifecycle is owned by core.supervision.
"""

from .state_store import StateStore
from .recovery_confidence import RecoveryConfidenceEngine

try:
    from core.supervision.supervisor import Supervisor as LifecycleSupervisor
except ImportError:  # pragma: no cover - keeps legacy imports lightweight
    LifecycleSupervisor = None


class RuntimeSupervisor:
    """Runtime-facing facade over the canonical supervision service."""

    def __init__(self, runtime=None, hooks=None, state_store=None, agent_id="default",
                 recovery=None, persistence=None, supervisor=None):
        self.runtime = runtime
        self.hooks = hooks
        self.state_store = state_store or StateStore()
        self.agent_id = agent_id
        self.running = False
        self.last_checkpoint = None
        self.health_status = "unknown"
        self.recovery_attempts = 0
        self.recovery_metrics = {"recoveries": 0, "rollbacks": 0, "failures": 0}
        self.decision_history = []
        self.confidence_engine = RecoveryConfidenceEngine()
        self.supervisor = supervisor
        if self.supervisor is None and LifecycleSupervisor:
            self.supervisor = LifecycleSupervisor(
                recovery=recovery,
                persistence=persistence,
            )

    def _emit(self, name, **metadata):
        if self.hooks:
            self.hooks.emit(name, **metadata)

    def observe(self, event, payload=None, component="runtime"):
        """Feed runtime health events into the canonical supervision lifecycle."""
        if event == "failure":
            self.health_status = "failed"
            self.recovery_attempts += 1
            self.recovery_metrics["failures"] += 1
        elif event == "success":
            self.health_status = "healthy"

        if self.supervisor:
            decision = self.supervisor.observe(component, event, payload)
            self._emit("supervision.observed", component=component, event=event, decision=decision)
            return decision

        return None

    def recovery_decision(self):
        """Return recovery analytics without creating a second recovery engine."""
        policy = self.state_store.policy(self.agent_id) if hasattr(self.state_store, "policy") else {}
        rollback_available = self.state_store.load(self.agent_id) is not None
        score = 0
        if self.health_status == "failed":
            score += 40
        if rollback_available:
            score += 30
        if self.recovery_attempts < policy.get("retries", 0):
            score += 20
        if policy.get("rollback", True):
            score += 10

        decision = {
            "agent_id": self.agent_id,
            "health": self.health_status,
            "score": score,
            "retry_available": self.recovery_attempts < policy.get("retries", 0),
            "rollback_available": rollback_available,
            "action": "rollback" if rollback_available else "retry",
        }
        confidence = self.confidence_engine.evaluate(decision)
        decision["confidence"] = confidence
        self.decision_history.append(decision)
        self._emit("recovery.intelligence", decision=decision)
        return decision

    def decision_history_snapshot(self):
        return list(self.decision_history)
