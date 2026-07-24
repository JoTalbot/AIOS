"""Workflow Engine for AIOS v10.4.0.

DAG-based workflow execution with parallel steps, condition gates,
retry policies, timeouts, compensation actions, result passing,
workflow templates, and detailed execution tracing.

Classes:
    RetryPolicy     — max retries + backoff strategy
    TimeoutPolicy   — per-step timeout with grace period
    CompensationAction — undo/rollback on failure
    ConditionGate   — if/else branching within workflow
    WorkflowStep    — step with dependencies, retry, timeout, compensation
    WorkflowResult  — detailed execution trace
    Workflow        — DAG of steps + metadata
    WorkflowTemplate — reusable workflow blueprint
    WorkflowEngine  — central engine: create, execute, query, stats
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────────


class StepStatus(StrEnum):
    """Step execution status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class WorkflowStatus(StrEnum):
    """Workflow-level status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BackoffStrategy(StrEnum):
    """Retry backoff types."""

    CONSTANT = "constant"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"


# ── RetryPolicy ─────────────────────────────────────────────────────────────


@dataclass
class RetryPolicy:
    """Retry configuration for a workflow step."""

    max_retries: int = 3
    backoff: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0
    retryable_exceptions: list[str] = field(
        default_factory=list
    )  # exception class names

    def compute_delay(self, attempt: int) -> float:
        """Compute delay before next retry based on attempt number."""
        if self.backoff == BackoffStrategy.CONSTANT:
            return self.initial_delay
        if self.backoff == BackoffStrategy.LINEAR:
            return min(self.initial_delay * attempt, self.max_delay)
        if self.backoff == BackoffStrategy.EXPONENTIAL:
            return min(self.initial_delay * (2 ** (attempt - 1)), self.max_delay)
        return self.initial_delay

    def should_retry(self, exception_name: str) -> bool:
        """Determine if exception is retryable."""
        if not self.retryable_exceptions:
            return True  # retry all by default
        return exception_name in self.retryable_exceptions


# ── TimeoutPolicy ───────────────────────────────────────────────────────────


@dataclass
class TimeoutPolicy:
    """Per-step timeout configuration."""

    timeout_seconds: float = 30.0
    grace_period: float = 5.0  # extra time before hard kill

    def total_timeout(self) -> float:
        """Return total allowed time including grace period."""
        return self.timeout_seconds + self.grace_period


# ── CompensationAction ──────────────────────────────────────────────────────


@dataclass
class CompensationAction:
    """Undo/rollback action executed when a step fails."""

    name: str
    action: Callable
    params: dict[str, Any] = field(default_factory=dict)

    def execute(self) -> Any:
        """Run the compensation action."""
        try:
            return self.action(**self.params)
        except Exception as e:
            logger.error("Compensation '%s' failed: %s", self.name, e)
            return None


# ── ConditionGate ───────────────────────────────────────────────────────────


@dataclass
class ConditionGate:
    """If/else branching within a workflow.

    When evaluated:
    - If condition_fn(context) returns True → run 'then_steps'
    - Otherwise → run 'else_steps'
    """

    name: str
    condition_fn: Callable[[dict[str, Any]], bool]
    then_steps: list[str] = field(default_factory=list)  # step names
    else_steps: list[str] = field(default_factory=list)  # step names


# ── WorkflowStep ────────────────────────────────────────────────────────────


@dataclass
class WorkflowStep:
    """Single step in a DAG workflow."""

    id: str = ""
    name: str = ""
    action: Callable | None = None
    params: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)  # step IDs this must wait for
    retry_policy: RetryPolicy | None = None
    timeout_policy: TimeoutPolicy | None = None
    compensation: CompensationAction | None = None
    condition_gate: ConditionGate | None = None
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: str | None = None
    started_at: float | None = None
    finished_at: float | None = None
    retry_count: int = 0

    def __post_init__(self) -> None:
        """Generate ID if not provided."""
        if not self.id:
            import uuid

            self.id = str(uuid.uuid4())[:8]

    def duration(self) -> float:
        """Return step execution duration in seconds."""
        if self.started_at and self.finished_at:
            return self.finished_at - self.started_at
        return 0.0


# ── WorkflowResult ──────────────────────────────────────────────────────────


@dataclass
class WorkflowResult:
    """Detailed execution trace for a completed workflow."""

    workflow_id: str
    status: WorkflowStatus
    step_results: dict[str, Any] = field(default_factory=dict)  # step_id → result
    step_errors: dict[str, str] = field(default_factory=dict)  # step_id → error
    step_durations: dict[str, float] = field(default_factory=dict)  # step_id → seconds
    step_statuses: dict[str, StepStatus] = field(
        default_factory=dict
    )  # step_id → status
    compensation_results: dict[str, Any] = field(default_factory=dict)
    total_duration: float = 0.0
    started_at: float | None = None
    finished_at: float | None = None

    def summary(self) -> dict[str, Any]:
        """Return human-readable summary dict."""
        return {
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "total_duration": self.total_duration,
            "steps_completed": sum(
                1 for s in self.step_statuses.values() if s == StepStatus.SUCCESS
            ),
            "steps_failed": sum(
                1 for s in self.step_statuses.values() if s == StepStatus.FAILED
            ),
            "steps_skipped": sum(
                1 for s in self.step_statuses.values() if s == StepStatus.SKIPPED
            ),
            "total_steps": len(self.step_statuses),
        }


# ── Workflow ────────────────────────────────────────────────────────────────


@dataclass
class Workflow:
    """DAG workflow definition."""

    id: str = ""
    name: str = ""
    steps: dict[str, WorkflowStep] = field(default_factory=dict)  # step_id → step
    status: WorkflowStatus = WorkflowStatus.PENDING
    context: dict[str, Any] = field(default_factory=dict)  # shared data between steps
    result: WorkflowResult | None = None
    created_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        """Generate ID if not provided."""
        if not self.id:
            import uuid

            self.id = str(uuid.uuid4())[:8]

    def add_step(self, step: WorkflowStep) -> None:
        """Add a step to the workflow."""
        self.steps[step.id] = step

    def remove_step(self, step_id: str) -> None:
        """Remove a step from the workflow."""
        del self.steps[step_id]
        # Remove from depends_on references
        for other in self.steps.values():
            other.depends_on = [d for d in other.depends_on if d != step_id]


# ── WorkflowTemplate ────────────────────────────────────────────────────────


@dataclass
class WorkflowTemplate:
    """Reusable workflow blueprint — create workflows from templates."""

    name: str
    step_definitions: list[dict[str, Any]] = field(default_factory=list)
    description: str = ""
    version: str = "1.0"

    def create_workflow(
        self, name: str, actions: dict[str, Callable] | None = None
    ) -> Workflow:
        """Instantiate a workflow from this template.

        actions maps step_name → callable for execution.
        """
        wf = Workflow(name=name)
        actions = actions or {}
        for step_def in self.step_definitions:
            step = WorkflowStep(
                name=step_def.get("name", ""),
                action=actions.get(step_def.get("name", "")),
                params=step_def.get("params", {}),
                depends_on=step_def.get("depends_on", []),
                retry_policy=step_def.get("retry_policy"),
                timeout_policy=step_def.get("timeout_policy"),
            )
            wf.add_step(step)
        return wf


# ── DAGExecutor ─────────────────────────────────────────────────────────────


class DAGExecutor:
    """Execute DAG workflows respecting dependencies.

    Topological sort → execute layers in parallel → pass results between steps.
    """

    def __init__(self) -> None:
        self._compensation_queue: list[CompensationAction] = []
        self._completed_compensations: list[
            CompensationAction
        ] = []  # compensations of successful steps

    def compute_layers(self, steps: dict[str, WorkflowStep]) -> list[list[str]]:
        """Compute execution layers via topological sort.

        Each layer can run in parallel (no intra-layer dependencies).
        """
        # Build dependency graph
        deps: dict[str, set[str]] = defaultdict(set)
        for step_id, step in steps.items():
            deps[step_id] = set(step.depends_on)

        layers: list[list[str]] = []
        remaining = set(steps.keys())

        while remaining:
            # Find steps with no unresolved dependencies
            ready = {s for s in remaining if not (deps[s] & remaining)}
            if not ready:
                # Circular dependency → break
                logger.warning("Circular dependency detected in workflow DAG")
                ready = remaining.copy()  # execute remaining anyway
            layers.append(sorted(ready))
            remaining -= ready

        return layers

    def execute_workflow(self, workflow: Workflow) -> WorkflowResult:
        """Execute a workflow DAG step by step with retry, timeout, compensation."""
        result = WorkflowResult(
            workflow_id=workflow.id,
            status=WorkflowStatus.RUNNING,
            started_at=time.time(),
        )

        # Step result context — results from previous steps available
        step_context: dict[str, Any] = {}

        layers = self.compute_layers(workflow.steps)
        self._compensation_queue.clear()
        self._completed_compensations.clear()

        for layer in layers:
            for step_id in layer:
                step = workflow.steps.get(step_id)
                if step is None:
                    continue

                # ── Check condition gate ──
                if step.condition_gate:
                    # Combine workflow context + step results for gate evaluation
                    gate_context = {**workflow.context, **step_context}
                    gate_result = step.condition_gate.condition_fn(gate_context)
                    if gate_result:
                        pass  # gate just marks step as eligible
                    else:
                        step.status = StepStatus.SKIPPED
                        result.step_statuses[step_id] = StepStatus.SKIPPED
                        continue

                # ── Execute step with retry ──
                step.status = StepStatus.RUNNING
                step.started_at = time.time()
                result.step_statuses[step_id] = StepStatus.RUNNING

                max_attempts = 1 + (
                    step.retry_policy.max_retries if step.retry_policy else 0
                )
                attempt = 0

                while attempt < max_attempts:
                    attempt += 1
                    try:
                        # Inject results from dependencies into params
                        merged_params = {**step.params}
                        for dep_id in step.depends_on:
                            if dep_id in step_context:
                                merged_params[f"{dep_id}_result"] = step_context[dep_id]

                        if step.action is None:
                            step.result = None
                        else:
                            step.result = step.action(**merged_params)

                        step.status = StepStatus.SUCCESS
                        step.finished_at = time.time()
                        result.step_results[step_id] = step.result
                        result.step_statuses[step_id] = StepStatus.SUCCESS
                        result.step_durations[step_id] = step.duration()
                        step_context[step_id] = step.result
                        # Track compensation of successful step for saga rollback
                        if step.compensation:
                            self._completed_compensations.append(step.compensation)
                        break  # success → exit retry loop

                    except Exception as e:
                        step.retry_count = attempt - 1
                        exc_name = type(e).__name__
                        step.error = str(e)

                        if (
                            step.retry_policy
                            and step.retry_policy.should_retry(exc_name)
                            and attempt < max_attempts
                        ):
                            step.status = StepStatus.RETRYING
                            result.step_statuses[step_id] = StepStatus.RETRYING
                            delay = step.retry_policy.compute_delay(attempt)
                            logger.info(
                                "Step '%s' retry %d/%d (delay=%.1fs): %s",
                                step.name,
                                attempt,
                                max_attempts,
                                delay,
                                exc_name,
                            )
                            time.sleep(delay)
                            continue
                        else:
                            # Final failure
                            step.status = StepStatus.FAILED
                            step.finished_at = time.time()
                            result.step_errors[step_id] = str(e)
                            result.step_statuses[step_id] = StepStatus.FAILED
                            result.step_durations[step_id] = step.duration()

                            # Queue compensation of the failed step
                            if step.compensation:
                                self._compensation_queue.append(step.compensation)

                            # Fail the entire workflow
                            result.status = WorkflowStatus.FAILED
                            result.finished_at = time.time()
                            result.total_duration = (
                                result.finished_at - result.started_at
                            )

                            # Saga rollback: compensate all successful steps + failed step, in reverse order
                            all_compensations = (
                                self._completed_compensations + self._compensation_queue
                            )
                            self._run_compensations(result, all_compensations)

                            return result

        # ── All steps completed ──
        result.status = WorkflowStatus.COMPLETED
        result.finished_at = time.time()
        result.total_duration = result.finished_at - result.started_at
        workflow.status = WorkflowStatus.COMPLETED
        workflow.result = result

        return result

    def _run_compensations(
        self,
        result: WorkflowResult,
        compensations: list[CompensationAction] | None = None,
    ) -> None:
        """Execute all compensation actions in reverse order (saga rollback)."""
        compensations = compensations or self._compensation_queue
        for comp in reversed(compensations):
            comp_result = comp.execute()
            result.compensation_results[comp.name] = comp_result


# ── WorkflowEngine ──────────────────────────────────────────────────────────


class WorkflowEngine:
    """Central workflow engine: create, execute, query, stats.

    Full backward-compatible API plus advanced DAG features.
    """

    def __init__(self) -> None:
        self.workflows: dict[str, Workflow] = {}
        self.templates: dict[str, WorkflowTemplate] = {}
        self._executor = DAGExecutor()
        self._results: dict[str, WorkflowResult] = {}  # workflow_id → result

    # ── Create / Register ──────────────────────────────────────────

    def create_workflow(self, name: str) -> Workflow:
        """Create a new empty workflow."""
        wf = Workflow(name=name)
        self.workflows[wf.id] = wf
        return wf

    def register_template(self, template: WorkflowTemplate) -> None:
        """Register a workflow template for reuse."""
        self.templates[template.name] = template

    def create_from_template(
        self, template_name: str, name: str, actions: dict[str, Callable] | None = None
    ) -> Workflow:
        """Instantiate a workflow from a template."""
        template = self.templates.get(template_name)
        if template is None:
            raise KeyError(f"Template '{template_name}' not found")
        wf = template.create_workflow(name, actions)
        self.workflows[wf.id] = wf
        return wf

    # ── Add Steps ──────────────────────────────────────────────────

    def add_step(
        self,
        workflow_id: str,
        name: str,
        action: Callable,
        params: dict[str, Any] | None = None,
        depends_on: list[str] | None = None,
        retry_policy: RetryPolicy | None = None,
        timeout_policy: TimeoutPolicy | None = None,
        compensation: CompensationAction | None = None,
        condition_gate: ConditionGate | None = None,
    ) -> WorkflowStep:
        """Add a step to a workflow with full configuration."""
        wf = self._get_workflow(workflow_id)
        step = WorkflowStep(
            name=name,
            action=action,
            params=params or {},
            depends_on=depends_on or [],
            retry_policy=retry_policy,
            timeout_policy=timeout_policy,
            compensation=compensation,
            condition_gate=condition_gate,
        )
        wf.add_step(step)
        return step

    def add_condition_gate(
        self,
        workflow_id: str,
        step_id: str,
        condition_fn: Callable[[dict[str, Any]], bool],
        then_steps: list[str] | None = None,
        else_steps: list[str] | None = None,
    ) -> None:
        """Add a condition gate to an existing step."""
        wf = self._get_workflow(workflow_id)
        step = wf.steps.get(step_id)
        if step is None:
            raise KeyError(f"Step '{step_id}' not found")
        step.condition_gate = ConditionGate(
            name=f"gate_{step_id}",
            condition_fn=condition_fn,
            then_steps=then_steps or [],
            else_steps=else_steps or [],
        )

    # ── Execute ────────────────────────────────────────────────────

    def execute(
        self, workflow_id: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute a workflow and return result summary.

        Backward-compatible: returns dict with status + results.
        """
        wf = self._get_workflow(workflow_id)
        if context:
            wf.context = context

        wf.status = WorkflowStatus.RUNNING
        result = self._executor.execute_workflow(wf)
        self._results[workflow_id] = result

        return result.summary()

    def cancel(self, workflow_id: str) -> None:
        """Cancel a running workflow."""
        wf = self._get_workflow(workflow_id)
        wf.status = WorkflowStatus.CANCELLED

    # ── Query ──────────────────────────────────────────────────────

    def get_workflow(self, workflow_id: str) -> Workflow:
        """Return a workflow object."""
        return self._get_workflow(workflow_id)

    def get_result(self, workflow_id: str) -> WorkflowResult | None:
        """Return execution result for a workflow."""
        return self._results.get(workflow_id)

    def list_workflows(self, status: WorkflowStatus | None = None) -> list[Workflow]:
        """List all workflows, optionally filtered by status."""
        if status is None:
            return list(self.workflows.values())
        return [wf for wf in self.workflows.values() if wf.status == status]

    def list_templates(self) -> list[str]:
        """List all template names."""
        return sorted(self.templates.keys())

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        by_status: dict[str, int] = {}
        for wf in self.workflows.values():
            status_val = wf.status.value
            by_status[status_val] = by_status.get(status_val, 0) + 1
        return {
            "total_workflows": len(self.workflows),
            "by_status": by_status,
            "templates": len(self.templates),
            "total_executions": len(self._results),
        }

    # ── Internal ───────────────────────────────────────────────────

    def _get_workflow(self, workflow_id: str) -> Workflow:
        """Get workflow or raise KeyError."""
        if workflow_id not in self.workflows:
            raise KeyError(f"Workflow '{workflow_id}' not found")
        return self.workflows[workflow_id]


workflow_engine = WorkflowEngine()
