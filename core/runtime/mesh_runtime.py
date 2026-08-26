"""AIOS runtime integration helpers for distributed agent mesh."""


class MeshRuntimeBridge:
    def __init__(self, supervisor, mesh):
        self.supervisor = supervisor
        self.mesh = mesh

    def publish_snapshot(self):
        snapshot = self.supervisor.observability_snapshot()
        return self.mesh.publish(
            event="agent.snapshot",
            source=self.supervisor.agent_id,
            payload=snapshot,
            broadcast=True,
        )

    def publish_recovery(self, decision):
        return self.mesh.publish(
            event="recovery.decision",
            source=self.supervisor.agent_id,
            payload={"decision": decision},
            broadcast=True,
        )

    def snapshot(self):
        return {
            "agent_id": self.supervisor.agent_id,
            "mesh": self.mesh.snapshot(),
            "runtime": self.supervisor.observability_snapshot(),
        }
