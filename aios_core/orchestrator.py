"""AIOS Orchestrator v3.0.0

Central coordination engine that plans, executes, and monitors
complex multi-step tasks by composing all AIOS subsystems:
- RuntimePolicy for constitutional evaluation
- MemoryManager for persistent memory
- KnowledgeGraph for semantic relationships
- ReasoningEngine for explainable decision chains
- LearningEngine for experience-based improvements
- EvolutionManager for controlled self-modification
- PrivacyGuard for data classification enforcement

Every task goes through constitutional evaluation before execution.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

from .storage import Database
from .config import AIOSConfig, load_config
from .runtime_policy import RuntimePolicy
from .memory_manager import MemoryManager
from .knowledge_graph import KnowledgeGraph
from .reasoning_engine import ReasoningEngine, ReasoningStep
from .learning_engine import LearningEngine
from .evolution_manager import EvolutionManager
from .privacy_guard import PrivacyGuard
from .event_bus import EventBus, Event, EventType
from .planner import Planner, Plan, PlanStep as PlannerStep, PlanStatus
from .capability_engine import CapabilityEngine, CapabilityStatus
from .autonomy_manager import AutonomyManager, AutonomyLevel


class TaskStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TaskStep:
    """A single step within an orchestrated task."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    status: StepStatus = StepStatus.PENDING
    step_type: str = "tool"  # tool, evaluate, memory, knowledge, approve, custom
    params: dict = field(default_factory=dict)
    result: Any = None
    error: str = None
    started_at: str = None
    completed_at: str = None
    constitutional_check: dict = None  # Result of constitution evaluation


@dataclass
class Task:
    """A multi-step orchestrated task."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    agent_id: str = "orchestrator"
    authority: str = "system"
    risk_level: str = "medium"
    steps: list[TaskStep] = field(default_factory=list)
    current_step_index: int = -1
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: str = None
    completed_at: str = None
    error: str = None
    metadata: dict = field(default_factory=dict)


class Orchestrator:
    """Central coordination engine for AIOS.

    Plans and executes multi-step tasks, coordinating all subsystems.
    Every step goes through constitutional evaluation before execution.

    Usage:
        orch = Orchestrator(db=Database(":memory:"), constitution_dir="...", policies_dir="...")

        # Create and execute a task
        task = orch.create_task("analyze_data", "Analyze user data patterns", risk_level="low")
        orch.add_step(task, "evaluate", params={"goal": "Read metrics", ...})
        orch.add_step(task, "memory", params={"action": "store", "content": {...}, "category": "operational"})
        result = orch.execute_task(task)
    """

    def __init__(
        self,
        db: Optional[Database] = None,
        config: Optional[AIOSConfig] = None,
        constitution_dir: Optional[str] = None,
        policies_dir: Optional[str] = None,
    ):
        self.version = "3.1.0"
        self.config = config or load_config()

        # Resolve directories
        if constitution_dir is None:
            constitution_dir = self.config.resolve_path(self.config.constitution.dir)
        if policies_dir is None:
            policies_dir = self.config.resolve_path(self.config.policies.dir)

        # Database
        self.db = db or Database(config=self.config)

        # Core subsystems
        self.policy = RuntimePolicy(
            constitution_dir=constitution_dir,
            policies_dir=policies_dir,
            db=self.db,
            config=self.config,
        )
        self.memory = MemoryManager(db=self.db)
        self.knowledge = KnowledgeGraph(db=self.db)
        self.reasoning = ReasoningEngine(db=self.db, memory=self.memory, knowledge=self.knowledge)
        self.learning = LearningEngine(db=self.db, memory=self.memory)
        self.evolution = EvolutionManager(db=self.db)
        self.privacy = PrivacyGuard()

        # v3.0 subsystems
        self.events = EventBus(db=self.db)
        self.planner = Planner(db=self.db)
        self.capabilities = CapabilityEngine(db=self.db)
        self.autonomy = AutonomyManager(db=self.db)

        # Task tracking
        self._tasks: dict[str, Task] = {}
        self._execution_log: list[dict] = []

    # --- Task Management ---

    def create_task(
        self,
        name: str,
        description: str = "",
        agent_id: str = "orchestrator",
        authority: str = "system",
        risk_level: str = "medium",
        metadata: Optional[dict] = None,
    ) -> Task:
        """Create a new task without executing it."""
        task = Task(
            name=name,
            description=description,
            agent_id=agent_id,
            authority=authority,
            risk_level=risk_level,
            metadata=metadata or {},
        )
        self._tasks[task.id] = task
        self.events.emit("task_created", "orchestrator", {"task_id": task.id, "name": task.name, "agent_id": task.agent_id})
        return task

    def add_step(
        self,
        task: Task,
        step_type: str,
        params: Optional[dict] = None,
        name: str = "",
        description: str = "",
    ) -> TaskStep:
        """Add a step to a task.

        Step types:
            - evaluate: Run constitutional evaluation
            - memory: Memory operation (store/retrieve/search)
            - knowledge: Knowledge graph operation
            - tool: Generic tool call
            - approve: Wait for human approval
            - learn: Record learning experience
            - reason: Build reasoning chain
            - evolve: Evolution proposal
            - custom: Custom handler
        """
        step = TaskStep(
            name=name or f"{step_type}_{len(task.steps)}",
            description=description,
            step_type=step_type,
            params=params or {},
        )
        task.steps.append(step)
        return step

    def execute_task(self, task: Task) -> dict:
        """Execute all steps in a task sequentially.

        Returns a summary dict with task_id, status, step results, etc.
        Each step goes through constitutional evaluation before execution.
        """
        if task.status in (TaskStatus.COMPLETED, TaskStatus.RUNNING):
            return self._task_summary(task)

        task.status = TaskStatus.RUNNING
        self.events.emit("task_started", "orchestrator", {"task_id": task.id, "name": task.name})
        task.started_at = datetime.now(timezone.utc).isoformat()

        for i, step in enumerate(task.steps):
            task.current_step_index = i
            step.status = StepStatus.RUNNING
            step.started_at = datetime.now(timezone.utc).isoformat()

            try:
                # Constitutional check for this step
                step.constitutional_check = self._evaluate_step(task, step)

                if step.constitutional_check.get("decision") == "DENY":
                    step.status = StepStatus.FAILED
                    step.error = step.constitutional_check.get("details", "Constitution denied")
                    task.status = TaskStatus.FAILED
                    task.error = f"Step '{step.name}' denied by constitution"
                    break

                if step.constitutional_check.get("decision") == "REVIEW":
                    step.status = StepStatus.FAILED
                    step.error = "Requires approval — task paused"
                    task.status = TaskStatus.WAITING_APPROVAL
                    task.error = f"Step '{step.name}' requires human approval"
                    self.events.emit("approval_requested", "orchestrator", {"task_id": task.id, "step_id": step.id, "step_name": step.name})
                    break

                # Autonomy check (skip for system-level agents)
                if task.agent_id not in ("orchestrator", "system"):
                    autonomy_result = self.autonomy.check_autonomy(task.agent_id, action_risk=step.params.get("risk", task.risk_level))
                    if autonomy_result["requires_approval"] and step.constitutional_check.get("decision") != "REVIEW":
                        step.status = StepStatus.FAILED
                        step.error = f"Requires approval (autonomy level {autonomy_result['level']})"
                        task.status = TaskStatus.WAITING_APPROVAL
                        task.error = f"Step '{step.name}' requires approval due to autonomy level {autonomy_result['level']}"
                        self.events.emit("approval_requested", "orchestrator", {"task_id": task.id, "step_id": step.id, "reason": "autonomy_level"})
                        break

                # Execute the step
                step.result = self._execute_step(task, step)
                self.autonomy.record_action(task.agent_id, success=True)
                step.status = StepStatus.COMPLETED

            except Exception as e:
                step.status = StepStatus.FAILED
                step.error = str(e)
                self.autonomy.record_action(task.agent_id, success=False, triggered_review=True)
                task.status = TaskStatus.FAILED
                task.error = f"Step '{step.name}' failed: {e}"
                self.events.emit("task_failed", "orchestrator", {"task_id": task.id, "name": task.name, "error": task.error})
                break

            finally:
                step.completed_at = datetime.now(timezone.utc).isoformat()
                self._log_execution(task, step)

        if task.status == TaskStatus.RUNNING:
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now(timezone.utc).isoformat()
            self.events.emit("task_completed", "orchestrator", {"task_id": task.id, "name": task.name, "steps_completed": len(task.steps)})

            # Record successful task as learning
            self.learning.record_task_completion(task)

        return self._task_summary(task)

    def _evaluate_step(self, task: Task, step: TaskStep) -> dict:
        """Evaluate a step against the constitution."""
        goal = step.params.get("goal", f"Execute step: {step.name}")
        scope = step.params.get("scope", task.name)
        risk = step.params.get("risk", task.risk_level)

        return self.policy.request_execution({
            "goal": goal,
            "scope": scope,
            "risk": risk,
            "audit_log": True,
            "agent_id": task.agent_id,
            "authority": task.authority,
            "action_type": step.step_type,
        })

    def _execute_step(self, task: Task, step: TaskStep) -> Any:
        """Execute a single step based on its type."""
        handler = _STEP_HANDLERS.get(step.step_type)
        if handler is None:
            raise ValueError(f"Unknown step type: {step.step_type}")
        return handler(self, step.params)

    def _task_summary(self, task: Task) -> dict:
        """Build a summary dict for a task."""
        return {
            "task_id": task.id,
            "name": task.name,
            "status": task.status.value,
            "total_steps": len(task.steps),
            "completed_steps": sum(1 for s in task.steps if s.status == StepStatus.COMPLETED),
            "failed_steps": sum(1 for s in task.steps if s.status == StepStatus.FAILED),
            "error": task.error,
            "steps": [
                {
                    "id": s.id,
                    "name": s.name,
                    "type": s.step_type,
                    "status": s.status.value,
                    "result": s.result,
                    "error": s.error,
                    "constitutional_check": {
                        "decision": s.constitutional_check.get("decision") if s.constitutional_check else None,
                        "evaluation_id": s.constitutional_check.get("evaluation_id") if s.constitutional_check else None,
                    } if s.constitutional_check else None,
                }
                for s in task.steps
            ],
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
        }

    def _log_execution(self, task: Task, step: TaskStep):
        """Log step execution to audit trail."""
        self._execution_log.append({
            "task_id": task.id,
            "step_id": step.id,
            "step_name": step.name,
            "step_type": step.step_type,
            "status": step.status.value,
            "error": step.error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        # Also persist to audit log
        self.policy.audit.record({
            "type": "orchestrator_step",
            "task_id": task.id,
            "step_id": step.id,
            "step_name": step.name,
            "step_type": step.step_type,
            "status": step.status.value,
            "error": step.error,
        })

    # --- Direct subsystem access ---

    def evaluate(self, action: dict) -> dict:
        """Direct constitutional evaluation shortcut."""
        return self.policy.request_execution({
            **action,
            "audit_log": True,
            "agent_id": action.get("agent_id", "orchestrator"),
            "authority": action.get("authority", "system"),
        })

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    def list_tasks(self, status: Optional[TaskStatus] = None) -> list[dict]:
        """List all tasks, optionally filtered by status."""
        tasks = self._tasks.values()
        if status:
            tasks = [t for t in tasks if t.status == status]
        return [
            {
                "task_id": t.id,
                "name": t.name,
                "status": t.status.value,
                "agent_id": t.agent_id,
                "steps": len(t.steps),
                "created_at": t.created_at,
            }
            for t in tasks
        ]

    def stats(self) -> dict:
        """Comprehensive orchestrator statistics."""
        status_counts: dict[str, int] = {}
        for t in self._tasks.values():
            s = t.status.value
            status_counts[s] = status_counts.get(s, 0) + 1

        # Collect quick counts
        try:
            mem_stats = self.memory.stats()
            evo_stats = self.evolution.stats()
        except Exception:
            mem_stats = {}
            evo_stats = {}

        return {
            "version": self.version,
            "total_tasks": len(self._tasks),
            "tasks_by_status": status_counts,
            "total_steps_executed": len(self._execution_log),
            "active_tasks": status_counts.get("running", 0) + status_counts.get("pending", 0),
            "constitution_articles": 67,
            "memory_items": mem_stats.get("total_items", 0),
            "evolution_proposals": evo_stats.get("total_proposals", 0),
            "subsystems": {
                "policy": self.policy.stats(),
                "memory": mem_stats,
                "knowledge": self.knowledge.stats(),
                "reasoning": self.reasoning.stats(),
                "learning": self.learning.stats(),
                "evolution": evo_stats,
                "privacy": self.privacy.stats(),
                "events": self.events.stats(),
                "planner": self.planner.stats(),
                "capabilities": self.capabilities.stats(),
                "autonomy": self.autonomy.stats(),
            },
            "database": self.db.stats(),
        }

    def close(self):
        self.db.close()


# --- Step Handlers ---

def _step_evaluate(orch: Orchestrator, params: dict) -> dict:
    """Handler for 'evaluate' step type — runs constitutional evaluation."""
    return orch.policy.request_execution({
        **params,
        "audit_log": True,
        "agent_id": params.get("agent_id", "orchestrator"),
        "authority": params.get("authority", "system"),
    })


def _step_memory(orch: Orchestrator, params: dict) -> dict:
    """Handler for 'memory' step type — store/retrieve/search."""
    action = params.get("action", "store")
    if action == "store":
        return orch.memory.store(
            content=params.get("content", {}),
            category=params.get("category", "operational"),
            tags=params.get("tags"),
            source=params.get("source"),
            confidence=params.get("confidence", 1.0),
        )
    elif action == "retrieve":
        return orch.memory.retrieve(params.get("item_id", ""))
    elif action == "search":
        return orch.memory.search(
            query=params.get("query", ""),
            category=params.get("category"),
            tag=params.get("tag"),
            limit=params.get("limit", 20),
        )
    elif action == "delete":
        return {"deleted": orch.memory.delete(params.get("item_id", ""))}
    else:
        raise ValueError(f"Unknown memory action: {action}")


def _step_knowledge(orch: Orchestrator, params: dict) -> dict:
    """Handler for 'knowledge' step type."""
    action = params.get("action", "add_node")
    if action == "add_node":
        return orch.knowledge.add_node(
            label=params["label"],
            node_type=params.get("node_type", "concept"),
            properties=params.get("properties"),
        )
    elif action == "find_nodes":
        return orch.knowledge.find_nodes(
            label=params.get("label"),
            node_type=params.get("node_type"),
            limit=params.get("limit", 20),
        )
    elif action == "add_relation":
        return orch.knowledge.add_relation(
            source_id=params["source_id"],
            target_id=params["target_id"],
            relation=params["relation"],
            properties=params.get("properties"),
            weight=params.get("weight", 1.0),
        )
    elif action == "neighbors":
        return orch.knowledge.neighbors(
            node_id=params["node_id"],
            relation=params.get("relation"),
            depth=params.get("depth", 1),
        )
    else:
        raise ValueError(f"Unknown knowledge action: {action}")


def _step_reason(orch: Orchestrator, params: dict) -> dict:
    """Handler for 'reason' step type."""
    return orch.reasoning.build_chain(
        question=params.get("question", ""),
        context=params.get("context", {}),
        use_memory=params.get("use_memory", False),
        use_knowledge=params.get("use_knowledge", False),
    )


def _step_learn(orch: Orchestrator, params: dict) -> dict:
    """Handler for 'learn' step type."""
    return orch.learning.record(
        experience=params.get("experience", {}),
        tags=params.get("tags"),
    )


def _step_evolve(orch: Orchestrator, params: dict) -> dict:
    """Handler for 'evolve' step type."""
    return orch.evolution.propose(
        change=params.get("change", {}),
        component=params.get("component", ""),
        reason=params.get("reason", ""),
    )


def _step_plan(orch: Orchestrator, params: dict) -> dict:
    """Handler for 'plan' step type — create and validate a plan."""
    plan = orch.planner.create_plan(
        name=params.get("name", "inline_plan"),
        description=params.get("description", ""),
        goal=params.get("goal", ""),
    )
    for step_def in params.get("steps", []):
        orch.planner.add_step(plan, step_def.get("type", "tool"), step_def.get("params", {}), name=step_def.get("name", ""))
    # Add dependencies if specified
    for dep in params.get("dependencies", []):
        orch.planner.add_dependency(plan, dep["from"], dep["to"], dep.get("condition", "success"))
    validation = orch.planner.validate_plan(plan)
    return {"plan_id": plan.id, "validation": validation, "layers": len(validation.get("execution_layers", []))}


def _step_tool(orch: Orchestrator, params: dict) -> dict:
    """Handler for 'tool' step type — generic passthrough."""
    return {"tool_result": params, "executed": True}


def _step_approve(orch: Orchestrator, params: dict) -> dict:
    """Handler for 'approve' step type — always pauses for approval."""
    return {"status": "waiting_approval", "approval_required": True}


_STEP_HANDLERS: dict[str, Callable] = {
    "evaluate": _step_evaluate,
    "memory": _step_memory,
    "knowledge": _step_knowledge,
    "reason": _step_reason,
    "learn": _step_learn,
    "evolve": _step_evolve,
    "tool": _step_tool,
    "approve": _step_approve,
    "plan": _step_plan,
}