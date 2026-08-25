"""Compose AIOS policy, runtime, execution and supervisor boundaries."""

from __future__ import annotations

from collections.abc import Mapping

from aios_core.execution import Action, ExecutionContext, ExecutionKernel, Observation
from aios_core.kernel import ExecutionContext as PolicyContext
from aios_core.kernel import Kernel as PolicyKernel
from aios_core.runtime import AgentBudget, AgentState, HeartbeatManager, LifecycleManager
from aios_core.supervisor import (
    AgentSupervisor,
    ExecutionGraph,
    ExecutionGraphBuilder,
    SupervisorDecision,
    SupervisorTask,
)


class ArchitectureRuntime:
    """Fail-closed composition of the v20 control and execution planes.

    ``PolicyKernel`` is the policy decision point. ``ExecutionKernel`` is the only
    capability side-effect boundary. Lifecycle, heartbeat, and budget checks are
    policy-enforcement preconditions. ``AgentSupervisor`` plans bounded specialist
    teams but never bypasses this execution path.
    """

    def __init__(
        self,
        *,
        policy: PolicyKernel,
        execution: ExecutionKernel,
        lifecycle: LifecycleManager,
        heartbeat: HeartbeatManager,
        budgets: Mapping[str, AgentBudget],
        supervisor: AgentSupervisor | None = None,
        graph_builder: ExecutionGraphBuilder | None = None,
    ) -> None:
        self.policy = policy
        self.execution = execution
        self.lifecycle = lifecycle
        self.heartbeat = heartbeat
        self.budgets = budgets
        self.supervisor = supervisor or AgentSupervisor()
        self.graph_builder = graph_builder or ExecutionGraphBuilder()

    def execute(self, action: Action, context: ExecutionContext) -> Observation:
        """Authorize and enforce one capability request before any side effect."""
        try:
            decision = self.policy.process(
                PolicyContext(
                    agent_id=context.agent_id,
                    action=action.capability,
                    metadata={"task_id": context.task_id, "authority": context.authority},
                )
            )
        except Exception as exc:
            return Observation.failed(action, f"policy_error:{exc}")

        if not decision.allowed:
            return Observation.failed(action, f"policy_denied:{decision.reason}")

        state = self.lifecycle.states.get(context.agent_id)
        if state is not AgentState.RUNNING:
            state_name = state.value if state is not None else "unknown"
            return Observation.failed(action, f"agent_not_running:{state_name}")
        if not self.heartbeat.alive(context.agent_id):
            return Observation.failed(action, "agent_heartbeat_stale")

        budget = self.budgets.get(context.agent_id)
        if budget is None:
            return Observation.failed(action, "agent_budget_missing")
        try:
            budget.consume()
        except RuntimeError as exc:
            return Observation.failed(action, str(exc))

        return self.execution.execute(action, context)

    def plan(self, task: SupervisorTask) -> tuple[SupervisorDecision, ExecutionGraph]:
        """Return a bounded specialist decision and its validated execution graph."""
        decision = self.supervisor.plan(task)
        return decision, self.graph_builder.build(decision)
