"""AIOS Runtime Policy Layer v2.1.1

Runtime enforcement layer for agent execution decisions.
"""

from .constitution_engine import ConstitutionEngine


class RuntimePolicy:
    """Enforces constitutional policies at runtime."""

    def __init__(self):
        self.engine = ConstitutionEngine()
        self.executions = []

    def request_execution(self, agent_action: dict) -> dict:
        """Request execution of an action.
        
        Args:
            agent_action: Agent action request
            
        Returns:
            Execution decision with allow/deny status
        """
        decision = self.engine.evaluate(agent_action)
        
        execution_result = {
            "allowed": decision["decision"] == "ALLOW",
            "decision": decision["decision"],
            "constitution_version": decision.get("constitution_version", "2.1.1"),
            "details": decision.get("details", ""),
        }
        
        self.executions.append(execution_result)
        return execution_result

    def history(self) -> list:
        """Return execution history."""
        return self.executions
