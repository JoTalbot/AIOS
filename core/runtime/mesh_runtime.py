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
        return self.mesh.publish(
            name="recovery.decision",
            source=self.supervisor.agent_id,
            target="broadcast",
            decision=decision,
        )

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

    def acknowledge(self, event):
        return self.mesh.acknowledge(event)

    def broadcast_recovery(self, decision):
        return self.publish_message(
            "recovery.broadcast",
            decision=decision,
            broadcast=True,
        )

    def snapshot(self):
        return {
            "agent_id": self.supervisor.agent_id,
            "mesh": self.mesh.snapshot(),
            "runtime": self.supervisor.observability_snapshot(),
        }
