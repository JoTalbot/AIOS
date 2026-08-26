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

    def snapshot(self):
        return {
            "agent_id": self.supervisor.agent_id,
            "mesh": self.mesh.snapshot(),
            "runtime": self.supervisor.observability_snapshot(),
        }
