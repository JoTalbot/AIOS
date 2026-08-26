"""AIOS v20 kernel execution loop.

Connects intent, policy, capabilities, lifecycle and memory layers.
"""

from dataclasses import dataclass


@dataclass
class ExecutionResult:
    success: bool
    stage: str
    details: dict


class KernelExecutor:
    """Minimal v20 execution coordinator."""

    def __init__(self, intent_engine, policy_engine, capability_registry,
                 lifecycle, memory):
        self.intent_engine = intent_engine
        self.policy_engine = policy_engine
        self.capability_registry = capability_registry
        self.lifecycle = lifecycle
        self.memory = memory

    def execute(self, agent, goal: str) -> ExecutionResult:
        intent = self.intent_engine.create(goal)

        if not self.policy_engine.allow(agent, intent):
            return ExecutionResult(False, "policy", {"intent": intent.name})

        self.lifecycle.start(agent)
        capability = self.capability_registry.resolve(intent.name)

        self.memory.remember({
            "agent": agent.name,
            "goal": goal,
            "capability": capability,
        })

        return ExecutionResult(
            True,
            "completed",
            {"intent": intent.name, "capability": capability},
        )
