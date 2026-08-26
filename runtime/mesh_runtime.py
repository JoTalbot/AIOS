"""AIOS runtime integration helpers for distributed agent mesh."""


class MeshRuntimeBridge:
    def __init__(self, supervisor, mesh):
        self.supervisor = supervisor
        self.mesh = mesh

    def publish_snapshot(self):
        snapshot = self.supervisor.observability_snapshot()
        return self.mesh.publish(
            name="agent.snapshot",
            source=self.supervisor.agent_id,
            target="broadcast",
            snapshot=snapshot,
        )

    def publish_recovery(self, decision):
        confidence = self._confidence(decision)
        return self.mesh.publish(
            name="recovery.decision",
            source=self.supervisor.agent_id,
            target="broadcast",
            decision=decision,
            confidence=confidence,
            priority=self._priority(confidence),
        )

    def _confidence(self, decision):
        if hasattr(self.supervisor, "recovery_confidence"):
            return self.supervisor.recovery_confidence(decision)
        score = decision.get("score", 0) if isinstance(decision, dict) else 0
        return min(100, max(0, score))

    def _priority(self, confidence):
        if confidence >= 80:
            return "high"
        if confidence >= 40:
            return "normal"
        return "low"

    def publish_recovery_decision(self):
        decision = self.supervisor.recovery_decision() if hasattr(self.supervisor, "recovery_decision") else {}
        return self.publish_recovery(decision)

    def publish_message(self, name, target="broadcast", **payload):
        return self.mesh.publish(
            name=name,
            source=self.supervisor.agent_id,
            target=target,
            **payload,
        )

    def subscribe(self, callback):
        return self.mesh.subscribe(callback)

    def unsubscribe(self, callback):
        return self.mesh.unsubscribe(callback)

    def register_delivery_callback(self, callback):
        return self.mesh.register_delivery_callback(callback)

    def unregister_delivery_callback(self, callback):
        return self.mesh.unregister_delivery_callback(callback)

    def register_recovery_callback(self, callback):
        return self.mesh.register_recovery_callback(callback)

    def unregister_recovery_callback(self, callback):
        return self.mesh.unregister_recovery_callback(callback)

    def acknowledge(self, event):
        return self.mesh.acknowledge(event)

    def recover(self, event, reason="delivery_failed"):
        return self.mesh.recover(event, reason=reason)

    def broadcast_recovery(self, decision):
        confidence = self._confidence(decision)
        return self.publish_message(
            "recovery.broadcast",
            decision=decision,
            confidence=confidence,
            priority=self._priority(confidence),
            broadcast=True,
        )

    def snapshot(self):
        return {
            "agent_id": self.supervisor.agent_id,
            "mesh": self.mesh.snapshot(),
            "runtime": self.supervisor.observability_snapshot(),
        }
