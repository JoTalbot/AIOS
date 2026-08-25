"""Route supervisor specialist roles through the governed architecture runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import TYPE_CHECKING, Any

from aios_core.execution import Action, ExecutionContext, Observation
from aios_core.supervisor import ExecutionGraph, ExecutionResult, SupervisorDecision

from .delegation import DelegationRegistry

if TYPE_CHECKING:
    from .runtime import ArchitectureRuntime


@dataclass(frozen=True)
class SpecialistInvocation:
    """Least-privilege tool intent assigned to one selected specialist role."""

    agent_id: str
    capability: str
    delegation_id: str
    arguments: dict[str, Any] = field(default_factory=dict)
    authority: str = "supervisor"


@dataclass(frozen=True)
class SupervisedRun:
    """Plan, graph, execution results, and governed observations."""

    decision: SupervisorDecision
    graph: ExecutionGraph
    results: tuple[ExecutionResult, ...]
    observations: dict[str, Observation]


class SupervisorRuntimeExecutor:
    """Callable ExecutionEngine adapter with no direct capability access."""

    def __init__(
        self,
        runtime: ArchitectureRuntime,
        *,
        task_id: str,
        invocations: dict[str, SpecialistInvocation],
        delegations: DelegationRegistry,
    ) -> None:
        self.runtime = runtime
        self.task_id = task_id
        self.invocations = dict(invocations)
        self.delegations = delegations
        self.observations: dict[str, Observation] = {}
        self._lock = Lock()

    def __call__(self, role: str) -> Observation:
        try:
            invocation = self.invocations[role]
        except KeyError as exc:
            raise RuntimeError(f"missing governed invocation for role: {role}") from exc

        self.delegations.validate(
            invocation.delegation_id,
            task_id=self.task_id,
            role=role,
            agent_id=invocation.agent_id,
            capability=invocation.capability,
        )
        observation = self.runtime.execute(
            Action(invocation.capability, dict(invocation.arguments)),
            ExecutionContext(
                task_id=self.task_id,
                agent_id=invocation.agent_id,
                authority=invocation.authority,
            ),
        )
        with self._lock:
            self.observations[role] = observation
        if not observation.success:
            raise RuntimeError(observation.error or "governed execution failed")
        return observation
