"""Autonomous recovery consensus execution layer."""

from datetime import datetime, timezone


class RecoveryConsensusExecution:
    """Executes approved recovery consensus decisions."""

    def __init__(self):
        self.executions = []

    def execute(self, consensus):
        action = consensus.get("decision", {}).get("action", "retry") if isinstance(consensus, dict) else "retry"
        result = {
            "action": action,
            "consensus": consensus,
            "status": "executed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.executions.append(result)
        return result

    def history(self):
        return list(self.executions)

    def snapshot(self):
        return {"executions": len(self.executions)}
