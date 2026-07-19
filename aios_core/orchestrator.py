"""AIOS Orchestrator Layer v2.1.1

Coordinates the core engines into a single cognitive lifecycle:

    perceive -> decide -> remember -> consensus -> execute -> evolve

It is the integration point that turns isolated engine modules into one
operating system.
"""

from .policy_loader import PolicyLoader
from .constitution_engine import ConstitutionEngine
from .decision_engine import DecisionEngine
from .approval_manager import ApprovalManager
from .memory_manager import MemoryManager
from .learning_engine import LearningEngine
from .consensus_engine import ConsensusEngine
from .evolution_manager import EvolutionManager
from .execution_manager import ExecutionManager


class Orchestrator:
    """Drives the AIOS cognitive lifecycle across all core engines."""

    def __init__(self, policy_loader=None):
        self.policies = policy_loader if policy_loader is not None else PolicyLoader()
        self.constitution = ConstitutionEngine(self.policies)
        self.decisions = DecisionEngine(self.policies)
        self.approval = ApprovalManager(self.policies)
        self.memory = MemoryManager()
        self.learning = LearningEngine()
        self.consensus = ConsensusEngine()
        self.evolution = EvolutionManager(policy_loader=self.policies)
        self.execution = ExecutionManager()
        self.traces = []

    def run(self, action: dict) -> dict:
        """Run an action through the full lifecycle and return a trace."""
        # 1. Constitutional evaluation
        verdict = self.constitution.evaluate(action)["decision"]

        # 2. Decision (with learned patterns informing confidence)
        decision = self.decisions.decide(action)

        # 3. Persist to memory
        mem = self.memory.store(
            {"action": action, "verdict": verdict}, category="operational"
        )

        # 4. Approval gate
        approval = self.approval.request(action)

        # 5. Consensus for non-trivial / global scope
        consensus = None
        if action.get("scope") in ("global", "constitution", "federation"):
            pid = self.consensus.submit(action, participants=3)
            self.consensus.vote(pid, "approve")
            self.consensus.vote(pid, "approve")
            consensus = self.consensus.reach_consensus(pid)

        # 6. Execution
        allowed = verdict == "ALLOW" and approval["status"] in (
            "auto_approved", "approved"
        )
        execution = (
            self.execution.execute(action) if allowed else
            {"status": "blocked", "reason": decision.get("constitutional_reason")}
        )

        # 7. Learn from the outcome
        outcome = "success" if allowed else "failure"
        self.learning.learn({
            "action": action.get("goal"),
            "outcome": outcome,
            "confidence": decision.get("confidence", 0.5),
        })

        trace = {
            "action": action,
            "verdict": verdict,
            "decision": decision,
            "memory_id": mem.get("id"),
            "approval": approval["status"],
            "consensus": consensus["status"] if consensus else "n/a",
            "execution": execution,
            "learned": outcome,
        }
        self.traces.append(trace)
        return trace

    def report(self) -> dict:
        """Summarise orchestrator state."""
        return {
            "version": self.constitution.version,
            "decisions": len(self.decisions.history()),
            "memories": self.memory.size(),
            "experiences": len(self.learning.history()),
            "success_rate": self.learning.success_rate(),
            "traces": len(self.traces),
        }
