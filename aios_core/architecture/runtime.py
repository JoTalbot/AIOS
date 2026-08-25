"""Compose AIOS policy, runtime, execution and supervisor boundaries."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

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

from .approval import ApprovalGate, ApprovalStatus
from .audit import ArchitectureAuditStore

if TYPE_CHECKING:
    from .supervisor_adapter import SpecialistInvocation, SupervisedRun


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
        approval: ApprovalGate | None = None,
        audit: ArchitectureAuditStore | None = None,
    ) -> None:
        self.policy = policy
        self.execution = execution
        self.lifecycle = lifecycle
        self.heartbeat = heartbeat
        self.budgets = budgets
        self.supervisor = supervisor or AgentSupervisor()
        self.graph_builder = graph_builder or ExecutionGraphBuilder()
        self.approval = approval
        self.audit = audit

    def execute(self, action: Action, context: ExecutionContext) -> Observation:
        """Authorize, approve, enforce, and audit one capability request."""
        try:
            decision = self.policy.process(
                PolicyContext(
                    agent_id=context.agent_id,
                    action=action.capability,
                    metadata={"task_id": context.task_id, "authority": context.authority},
                )
            )
        except Exception as exc:
            return self._deny(action, context, "policy_error", str(exc))

        self._record("policy_decision", action, context, {"allowed": decision.allowed, "reason": decision.reason})
        if not decision.allowed:
            return self._deny(action, context, "policy_denied", decision.reason)

        if self.approval is not None and self.approval.requires(action.capability):
            request = self.approval.request(
                action_id=action.id,
                task_id=context.task_id,
                agent_id=context.agent_id,
                capability=action.capability,
            )
            if request.status is ApprovalStatus.PENDING:
                return self._deny(action, context, "approval_pending", action.id)
            if request.status is ApprovalStatus.REJECTED:
                return self._deny(action, context, "approval_rejected", request.decided_by or "unknown")
            if request.status is ApprovalStatus.CONSUMED:
                return self._deny(action, context, "approval_replay", action.id)
            if not self.approval.consume(action.id):
                return self._deny(action, context, "approval_invalid", action.id)
            self._record("approval_consumed", action, context, {"decided_by": request.decided_by})

        state = self.lifecycle.states.get(context.agent_id)
        if state is not AgentState.RUNNING:
            state_name = state.value if state is not None else "unknown"
            return self._deny(action, context, "agent_not_running", state_name)
        if not self.heartbeat.alive(context.agent_id):
            return self._deny(action, context, "agent_heartbeat_stale", "")

        budget = self.budgets.get(context.agent_id)
        if budget is None:
            return self._deny(action, context, "agent_budget_missing", "")
        try:
            budget.consume()
        except RuntimeError as exc:
            return self._deny(action, context, "agent_budget", str(exc))

        observation = self.execution.execute(action, context)
        self._record(
            "execution_completed" if observation.success else "execution_failed",
            action,
            context,
            {"success": observation.success, "error": observation.error},
        )
        return observation

    def _deny(self, action: Action, context: ExecutionContext, reason: str, detail: str) -> Observation:
        error = f"{reason}:{detail}" if detail else reason
        self._record("execution_denied", action, context, {"reason": reason, "detail": detail})
        return Observation.failed(action, error)

    def _record(
        self,
        event: str,
        action: Action,
        context: ExecutionContext,
        payload: dict[str, object],
    ) -> None:
        if self.audit is not None:
            self.audit.append(
                event,
                task_id=context.task_id,
                action_id=action.id,
                agent_id=context.agent_id,
                payload=payload,
            )

    def plan(self, task: SupervisorTask) -> tuple[SupervisorDecision, ExecutionGraph]:
        """Return a bounded specialist decision and its validated execution graph."""
        decision = self.supervisor.plan(task)
        return decision, self.graph_builder.build(decision)

    def run_supervised(
        self,
        task: SupervisorTask,
        invocations: Mapping[str, SpecialistInvocation],
    ) -> SupervisedRun:
        """Plan specialists and execute every role through this governed runtime."""
        from aios_core.supervisor import ExecutionEngine

        from .supervisor_adapter import SupervisedRun, SupervisorRuntimeExecutor

        decision, graph = self.plan(task)
        adapter = SupervisorRuntimeExecutor(
            self,
            task_id=task.task_id,
            invocations=dict(invocations),
        )
        results = ExecutionEngine(adapter, max_agents=task.budget_agents).run(graph)
        return SupervisedRun(decision, graph, results, dict(adapter.observations))
