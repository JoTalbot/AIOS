"""Runtime supervisor foundation with adaptive recovery analytics and observability."""

from .state_store import StateStore


class RuntimeSupervisor:
    def __init__(self, runtime=None, hooks=None, state_store=None, agent_id="default"):
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

    def _emit(self, name, **metadata):
        if self.hooks:
            self.hooks.emit(name, **metadata)

    async def _emit_async(self, name, **metadata):
        if self.hooks and hasattr(self.hooks, "emit_async"):
            await self.hooks.emit_async(name, **metadata)

    def checkpoint(self, state):
        self.last_checkpoint = dict(state) if isinstance(state, dict) else state
        self.state_store.save(self.agent_id, self.last_checkpoint)
        self.health_status = "healthy"
        self._emit("state.checkpoint", agent_id=self.agent_id)

    def start(self):
        restored = self.state_store.load(self.agent_id)
        self.running = True
        self.health_status = "healthy"
        self._emit("runtime.start", running=self.running, restored_state=restored)
        if restored is not None:
            self._emit("state.restored", agent_id=self.agent_id, state=restored)
        return restored

    def recover(self):
        self.recovery_attempts += 1
        self.recovery_metrics["recoveries"] += 1
        policy = self.state_store.policy(self.agent_id) if hasattr(self.state_store, "policy") else {}
        state = self.state_store.load(self.agent_id)
        decision = self.recovery_decision()
        self._emit("recovery.analytics", agent_id=self.agent_id, metrics=self.recovery_metrics)
        self._emit("recovery.decision", agent_id=self.agent_id, decision=decision, policy=policy)
        if state is not None:
            self.health_status = "healthy"
        return state

    def recovery_decision(self):
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
        self.decision_history.append(decision)
        self._emit("recovery.intelligence", decision=decision)
        return decision

    def fail(self, error):
        self.running = False
        self.health_status = "failed"
        self.recovery_metrics["failures"] += 1
        restored = self.recover()
        self._emit("runtime.error", error=str(error), recovery_state=restored)
        if restored is not None:
            self.recovery_metrics["rollbacks"] += 1
            self._emit("state.rollback", agent_id=self.agent_id, state=restored)
        return restored

    def decision_history_snapshot(self):
        return list(self.decision_history)

    def analytics(self):
        return {"agent_id": self.agent_id, "health": self.health_status, "attempts": self.recovery_attempts, "metrics": dict(self.recovery_metrics), "state_metrics": self.state_store.metrics(self.agent_id) if hasattr(self.state_store, "metrics") else {}}

    def observability_snapshot(self):
        snapshot = self.analytics()
        snapshot["decision_history"] = self.decision_history_snapshot()
        self._emit("observability.snapshot", agent_id=self.agent_id, snapshot=snapshot)
        return snapshot

    def fleet_snapshot(self):
        snapshot = {self.agent_id: self.observability_snapshot()}
        self._emit("fleet.snapshot", agents=list(snapshot.keys()))
        return snapshot

    def health(self):
        return {"agent_id": self.agent_id, "status": self.health_status, "running": self.running, "recovery_attempts": self.recovery_attempts, "recovery_metrics": dict(self.recovery_metrics)}
