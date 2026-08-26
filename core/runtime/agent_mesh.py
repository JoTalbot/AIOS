"""Distributed agent mesh coordination primitives."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List


@dataclass
class MeshEvent:
    name: str
    source: str
    target: str = "broadcast"
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False
    delivery_status: str = "pending"
    retries: int = 0


class AgentMesh:
    """Lightweight coordination bus with delivery recovery intelligence."""

    def __init__(self):
        self._events: List[MeshEvent] = []
        self._subscribers: List[Callable[[MeshEvent], None]] = []
        self._delivery_callbacks: List[Callable[[MeshEvent], None]] = []
        self._recovery_callbacks: List[Callable[[MeshEvent], None]] = []
        self._decision_history: List[Dict[str, Any]] = []
        self._decision_scores: Dict[str, int] = {}
        self._recovery_metrics: Dict[str, int] = {"failures": 0, "recoveries": 0, "retries": 0}

    def publish(self, name: str, source: str, target: str = "broadcast", **payload):
        event = MeshEvent(name=name, source=source, target=target, payload=payload)
        self._events.append(event)
        self._deliver(event)
        return event

    def subscribe(self, callback):
        self._subscribers.append(callback)
        return callback

    def unsubscribe(self, callback):
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def register_delivery_callback(self, callback):
        self._delivery_callbacks.append(callback)
        return callback

    def unregister_delivery_callback(self, callback):
        if callback in self._delivery_callbacks:
            self._delivery_callbacks.remove(callback)

    def register_recovery_callback(self, callback):
        self._recovery_callbacks.append(callback)
        return callback

    def unregister_recovery_callback(self, callback):
        if callback in self._recovery_callbacks:
            self._recovery_callbacks.remove(callback)

    def publish_decision(self, decision, source="system"):
        score = self.score_decision(decision)
        record = {"source": source, "decision": decision, "score": score, "timestamp": datetime.now(timezone.utc).isoformat()}
        self._decision_history.append(record)
        return self.publish("recovery.decision", source=source, decision=decision, score=score)

    def score_decision(self, decision):
        score = 0
        if decision.get("retry") or decision.get("retry_available"):
            score += 1
        if decision.get("rollback") or decision.get("rollback_available"):
            score += 2
        if decision.get("health") == "healthy":
            score += 2
        self._decision_scores[str(decision)] = score
        return score

    def decision_history(self):
        return list(self._decision_history)

    def _deliver(self, event):
        try:
            for callback in list(self._subscribers):
                callback(event)
            event.delivery_status = "delivered"
        except Exception:
            self._recovery_metrics["failures"] += 1
            self.recover(event)
        for callback in list(self._delivery_callbacks):
            callback(event)

    def recover(self, event):
        event.retries += 1
        self._recovery_metrics["recoveries"] += 1
        self._recovery_metrics["retries"] += 1
        event.delivery_status = "recovering"
        for callback in list(self._recovery_callbacks):
            callback(event)
        return event

    def acknowledge(self, event):
        event.acknowledged = True
        event.delivery_status = "acknowledged"
        return event

    def recovery_metrics(self):
        return dict(self._recovery_metrics)

    def events(self, target=None):
        if target is None:
            return list(self._events)
        return [event for event in self._events if event.target in (target, "broadcast")]

    def clear(self):
        self._events.clear()

    def snapshot(self):
        return {"events": len(self._events), "agents": sorted({event.source for event in self._events}), "subscribers": len(self._subscribers), "delivery_callbacks": len(self._delivery_callbacks), "recovery_callbacks": len(self._recovery_callbacks), "acknowledged": sum(event.acknowledged for event in self._events), "recovery_metrics": self.recovery_metrics(), "decisions": len(self._decision_history), "scored_decisions": len(self._decision_scores)}
