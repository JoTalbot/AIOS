"""AIOS Planner Engine v3.0.0

DAG-based task planner with parallel execution support.  Plans are composed
of typed steps connected by dependency edges forming a directed acyclic graph.
The planner validates cycles, computes topological execution layers, estimates
duration, and tracks progress through the graph.

Step types mirror the orchestrator: evaluate, memory, knowledge, tool, reason,
learn, evolve, approve, custom, plan.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from .storage import Database

from .storage import Database

__all__ = ["PlanStatus", "StepStatus", "EdgeCondition", "PlanStep", "PlanEdge", "Plan", "Planner"]

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PlanStatus(str, Enum):
    DRAFT = "draft"
    PLANNED = "planned"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class EdgeCondition(str, Enum):
    SUCCESS = "success"  # Only proceed if source completed successfully
    COMPLETION = "completion"  # Proceed if source completed (even with failure)
    ALWAYS = "always"  # Always proceed, regardless of source outcome


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class PlanStep:
    """A single node in the execution DAG."""

    id: str = field(default_factory=Database.new_id)
    name: str = ""
    step_type: str = "tool"
    params: dict = field(default_factory=dict)
    status: StepStatus = StepStatus.PENDING
    dependencies: list[str] = field(default_factory=list)
    result: Any = None
    error: str = None
    started_at: str = None
    completed_at: str = None
    constitutional_check: dict = None


@dataclass
class PlanEdge:
    """A directed dependency edge between two steps.

    source_id must complete before target_id can run.
    The condition determines under what circumstances the dependency
    is considered satisfied.
    """

    source_id: str = ""
    target_id: str = ""
    condition: str = "success"  # success | completion | always


@dataclass
class Plan:
    """A DAG-based execution plan."""

    id: str = field(default_factory=Database.new_id)
    name: str = ""
    description: str = ""
    goal: str = ""
    steps: list[PlanStep] = field(default_factory=list)
    edges: list[PlanEdge] = field(default_factory=list)
    status: PlanStatus = PlanStatus.DRAFT
    created_at: str = field(default_factory=Database.now_iso)
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Valid step types (mirrors orchestrator)
# ---------------------------------------------------------------------------

VALID_STEP_TYPES = frozenset(
    {
        "evaluate",
        "memory",
        "knowledge",
        "tool",
        "reason",
        "learn",
        "evolve",
        "approve",
        "custom",
        "plan",
    }
)


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------


class Planner:
    """DAG-based task planner with parallel execution support.

    Creates, validates, persists, and tracks execution progress of plans
    composed of typed steps connected by dependency edges.

    Usage:
        planner = Planner(db=Database(":memory:"))
        plan = planner.create_plan("my_plan", "Do things", "Achieve X")
        s1 = planner.add_step(plan, "memory", {"action": "store", ...})
        s2 = planner.add_step(plan, "tool", {...}, dependencies=[s1.id])
        result = planner.validate_plan(plan)
        plan = planner.save_plan(plan)
    """

    def __init__(self, db: Optional[Database] = None):
        self.db = db
        self._ensure_table()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _ensure_table(self) -> None:
        """Create the plans table and indexes if they do not exist."""
        if self.db is None:
            return
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS plans (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                description TEXT,
                goal        TEXT,
                steps_data  TEXT,
                edges_data  TEXT,
                status      TEXT NOT NULL DEFAULT 'draft',
                created_at  TEXT NOT NULL,
                updated_at  TEXT,
                metadata    TEXT
            )
        """
        )
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_plans_status ON plans(status)")
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_plans_created ON plans(created_at)")

    # ------------------------------------------------------------------
    # Plan CRUD
    # ------------------------------------------------------------------

    def create_plan(
        self,
        name: str,
        description: str = "",
        goal: str = "",
        metadata: Optional[dict] = None,
    ) -> Plan:
        """Create a new plan with status *draft*.

        Returns:
            A new :class:`Plan` instance (not yet persisted).
        """
        plan = Plan(
            name=name,
            description=description,
            goal=goal,
            status=PlanStatus.DRAFT,
            metadata=metadata or {},
        )
        return plan

    def save_plan(self, plan: Plan) -> Plan:
        """Persist a plan to the database (upsert).

        Returns the same plan object for convenience.
        """
        if self.db is None:
            return plan

        steps_data = Database.to_json(self._serialize_steps(plan.steps))
        edges_data = Database.to_json(self._serialize_edges(plan.edges))
        now = Database.now_iso()

        existing = self.db.query_one("SELECT id FROM plans WHERE id = ?", (plan.id,))
        if existing:
            self.db.execute(
                """UPDATE plans
                   SET name = ?, description = ?, goal = ?,
                       steps_data = ?, edges_data = ?, status = ?,
                       updated_at = ?, metadata = ?
                   WHERE id = ?""",
                (
                    plan.name,
                    plan.description,
                    plan.goal,
                    steps_data,
                    edges_data,
                    plan.status.value,
                    now,
                    Database.to_json(plan.metadata) if plan.metadata else None,
                    plan.id,
                ),
            )
        else:
            self.db.execute(
                """INSERT INTO plans
                       (id, name, description, goal, steps_data, edges_data,
                        status, created_at, updated_at, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    plan.id,
                    plan.name,
                    plan.description,
                    plan.goal,
                    steps_data,
                    edges_data,
                    plan.status.value,
                    plan.created_at,
                    now,
                    Database.to_json(plan.metadata) if plan.metadata else None,
                ),
            )
        return plan

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        """Retrieve a plan by ID.  Returns *None* if not found."""
        if self.db is None:
            return None
        row = self.db.query_one("SELECT * FROM plans WHERE id = ?", (plan_id,))
        if row is None:
            return None
        return self._row_to_plan(row)

    def list_plans(self, status: str | None = None, limit: int = 100) -> list[dict]:
        """List plans, optionally filtered by status.

        Returns a list of summary dicts (not full Plan objects).
        """
        if self.db is None:
            return []

        if status:
            rows = self.db.query(
                "SELECT * FROM plans WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            )
        else:
            rows = self.db.query(
                "SELECT * FROM plans ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )

        return [
            {
                "id": r["id"],
                "name": r["name"],
                "description": r["description"],
                "goal": r["goal"],
                "status": r["status"],
                "step_count": (len(Database.from_json(r["steps_data"])) if r["steps_data"] else 0),
                "edge_count": (len(Database.from_json(r["edges_data"])) if r["edges_data"] else 0),
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            }
            for r in rows
        ]

    def delete_plan(self, plan_id: str) -> bool:
        """Delete a plan.  Returns *True* if a row was deleted."""
        if self.db is None:
            return False
        cursor = self.db.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
        return cursor.rowcount > 0

    # ------------------------------------------------------------------
    # Step & Edge management
    # ------------------------------------------------------------------

    def add_step(
        self,
        plan: Plan,
        step_type: str,
        params: Optional[dict] = None,
        name: str = "",
        dependencies: Optional[list[str]] = None,
    ) -> PlanStep:
        """Add a step to a plan.

        Args:
            plan: The plan to modify.
            step_type: One of the valid step types.
            params: Parameters for the step.
            name: Human-readable name (auto-generated if empty).
            dependencies: List of step IDs this step depends on.

        Returns:
            The newly created :class:`PlanStep`.
        """
        if step_type not in VALID_STEP_TYPES:
            step_type = "custom"

        step = PlanStep(
            name=name or f"{step_type}_{len(plan.steps)}",
            step_type=step_type,
            params=params or {},
            dependencies=list(dependencies) if dependencies else [],
        )
        plan.steps.append(step)

        # Auto-create edges for declared dependencies
        for dep_id in step.dependencies:
            # Avoid duplicate edges
            already = any(e.source_id == dep_id and e.target_id == step.id for e in plan.edges)
            if not already:
                plan.edges.append(
                    PlanEdge(
                        source_id=dep_id,
                        target_id=step.id,
                        condition="success",
                    )
                )

        return step

    def add_dependency(
        self,
        plan: Plan,
        source_step_id: str,
        target_step_id: str,
        condition: str = "success",
    ) -> PlanEdge:
        """Add an explicit dependency edge between two steps.

        Also appends the source to the target's *dependencies* list
        if not already present.
        """
        if condition not in ("success", "completion", "always"):
            condition = "success"

        # Prevent duplicate edges
        for e in plan.edges:
            if e.source_id == source_step_id and e.target_id == target_step_id:
                e.condition = condition
                return e

        edge = PlanEdge(
            source_id=source_step_id,
            target_id=target_step_id,
            condition=condition,
        )
        plan.edges.append(edge)

        # Keep the step's dependencies list in sync
        target_step = self._find_step(plan, target_step_id)
        if target_step is not None and source_step_id not in target_step.dependencies:
            target_step.dependencies.append(source_step_id)

        return edge

    # ------------------------------------------------------------------
    # DAG Validation
    # ------------------------------------------------------------------

    def validate_plan(self, plan: Plan) -> dict:
        """Validate a plan's DAG structure.

        Checks for:
        - Circular dependencies (DFS with 3-coloring)
        - Missing dependency references (dangling edges)
        - Disconnected steps (no path from any root)

        Returns:
            ``{"valid": bool, "errors": list[str], "execution_layers": list[list[str]]}``
        """
        errors: list[str] = []

        step_ids = {s.id for s in plan.steps}

        # --- Check missing references ---
        seen_missing: set[tuple[str, str]] = set()
        for edge in plan.edges:
            if edge.source_id not in step_ids:
                key = ("source", edge.source_id, edge.target_id)
                if key not in seen_missing:
                    errors.append(
                        f"Edge references unknown source step '{edge.source_id}' "
                        f"(target: '{edge.target_id}')"
                    )
                    seen_missing.add(key)
            if edge.target_id not in step_ids:
                key = ("target", edge.source_id, edge.target_id)
                if key not in seen_missing:
                    errors.append(
                        f"Edge references unknown target step '{edge.target_id}' "
                        f"(source: '{edge.source_id}')"
                    )
                    seen_missing.add(key)

        # Also check step-level dependency references
        for step in plan.steps:
            for dep_id in step.dependencies:
                if dep_id not in step_ids:
                    errors.append(
                        f"Step '{step.name}' ({step.id}) depends on " f"unknown step '{dep_id}'"
                    )

        # --- Build adjacency list (only from valid edges) ---
        adj: dict[str, list[str]] = {s.id: [] for s in plan.steps}
        in_degree: dict[str, int] = {s.id: 0 for s in plan.steps}

        for edge in plan.edges:
            if edge.source_id in step_ids and edge.target_id in step_ids:
                adj[edge.source_id].append(edge.target_id)
                in_degree[edge.target_id] += 1

        # --- Cycle detection (DFS with white/gray/black coloring) ---
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {sid: WHITE for sid in step_ids}
        parent: dict[str, str | None] = {sid: None for sid in step_ids}

        def _dfs_cycle(node: str) -> Optional[list[str]]:
            """Return a cycle path if one is found from *node*, else None."""
            color[node] = GRAY
            for neighbor in adj.get(node, []):
                if color[neighbor] == GRAY:
                    # Reconstruct the cycle
                    cycle = [neighbor, node]
                    cur = node
                    while cur != neighbor:
                        cur = parent[cur]
                        if cur is None:
                            break
                        cycle.append(cur)
                    cycle.reverse()
                    return cycle
                if color[neighbor] == WHITE:
                    parent[neighbor] = node
                    result = _dfs_cycle(neighbor)
                    if result is not None:
                        return result
            color[node] = BLACK
            return None

        cycle_found: Optional[list[str]] = None
        for sid in step_ids:
            if color[sid] == WHITE:
                result = _dfs_cycle(sid)
                if result is not None:
                    cycle_found = result
                    break

        if cycle_found is not None:
            readable = " -> ".join(self._step_label(plan, sid) for sid in cycle_found)
            errors.append(f"Circular dependency detected: {readable}")

        # --- Disconnected steps (no path from any root) ---
        if not cycle_found and plan.steps:
            # Find all nodes reachable from roots (in_degree == 0)
            roots = [sid for sid, deg in in_degree.items() if deg == 0]
            reachable: set[str] = set()
            for root in roots:
                self._dfs_reachable(root, adj, reachable)

            disconnected = step_ids - reachable
            if disconnected:
                for did in sorted(disconnected):
                    label = self._step_label(plan, did)
                    errors.append(
                        f"Disconnected step '{label}' ({did}): " f"no path from any root step"
                    )

        # --- Execution layers ---
        execution_layers: list[list[str]] = []
        if not cycle_found and plan.steps:
            execution_layers = self._compute_layers_kahn(in_degree, adj)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "execution_layers": execution_layers,
        }

    # ------------------------------------------------------------------
    # Topological sort – execution layers (Kahn's algorithm)
    # ------------------------------------------------------------------

    def get_execution_layers(self, plan: Plan) -> list[list[str]]:
        """Compute parallel execution layers via Kahn's algorithm.

        Layer 0: steps with no dependencies.
        Layer 1: steps whose dependencies are all in layer 0.
        etc.

        Steps within a single layer can be executed in parallel.

        Raises:
            ValueError: If the plan contains a cycle.
        """
        step_ids = {s.id for s in plan.steps}

        adj: dict[str, list[str]] = {s.id: [] for s in plan.steps}
        in_degree: dict[str, int] = {s.id: 0 for s in plan.steps}

        for edge in plan.edges:
            if edge.source_id in step_ids and edge.target_id in step_ids:
                adj[edge.source_id].append(edge.target_id)
                in_degree[edge.target_id] += 1

        # Quick cycle check before running Kahn
        if self._has_cycle(adj, step_ids):
            raise ValueError("Cannot compute execution layers: plan contains a cycle")

        return self._compute_layers_kahn(in_degree, adj)

    def estimate_duration(self, plan: Plan, avg_step_ms: int = 100) -> dict:
        """Estimate total execution time based on parallel layers.

        Args:
            plan: The plan to estimate.
            avg_step_ms: Average duration of a single step in milliseconds.

        Returns:
            ``{"layers": int, "total_steps": int, "sequential_steps": int, "estimated_ms": int}``
        """
        layers = self.get_execution_layers(plan)
        total_steps = sum(len(layer) for layer in layers)
        sequential_steps = len(layers)  # Each layer is one sequential "round"
        estimated_ms = sequential_steps * avg_step_ms

        return {
            "layers": sequential_steps,
            "total_steps": total_steps,
            "sequential_steps": sequential_steps,
            "estimated_ms": estimated_ms,
        }

    # ------------------------------------------------------------------
    # Execution progress helpers
    # ------------------------------------------------------------------

    def get_ready_steps(self, plan: Plan) -> list[PlanStep]:
        """Return steps whose dependencies are all completed.

        Only considers steps that are currently PENDING or READY.
        """
        completed_ids = {s.id for s in plan.steps if s.status == StepStatus.COMPLETED}
        failed_ids = {s.id for s in plan.steps if s.status == StepStatus.FAILED}

        ready: list[PlanStep] = []
        for step in plan.steps:
            if step.status not in (StepStatus.PENDING, StepStatus.READY):
                continue
            if not step.dependencies:
                ready.append(step)
                continue

            # Check edge conditions for each dependency
            all_satisfied = True
            for dep_id in step.dependencies:
                edge_cond = self._get_edge_condition(plan, dep_id, step.id)
                if edge_cond == "always":
                    # Dependency is always considered satisfied
                    continue
                if edge_cond == "success":
                    if dep_id not in completed_ids:
                        all_satisfied = False
                        break
                else:  # completion
                    if dep_id not in completed_ids and dep_id not in failed_ids:
                        all_satisfied = False
                        break

            if all_satisfied:
                ready.append(step)

        return ready

    def mark_step_completed(
        self, plan: Plan, step_id: str, result: Any = None
    ) -> Optional[PlanStep]:
        """Mark a step as completed and update dependent step statuses.

        Returns the updated step, or *None* if not found.
        """
        step = self._find_step(plan, step_id)
        if step is None:
            return None

        step.status = StepStatus.COMPLETED
        step.result = result
        step.completed_at = Database.now_iso()

        # Promote dependent PENDING steps to READY if all deps are met
        self._refresh_dependent_statuses(plan)

        # Check if the entire plan is done
        self._check_plan_completion(plan)

        return step

    def mark_step_failed(self, plan: Plan, step_id: str, error: str = "") -> Optional[PlanStep]:
        """Mark a step as failed and propagate failure to dependents.

        For edges with condition "success", dependent steps are skipped.
        For edges with condition "completion" or "always", dependents may
        still proceed.

        Returns the updated step, or *None* if not found.
        """
        step = self._find_step(plan, step_id)
        if step is None:
            return None

        step.status = StepStatus.FAILED
        step.error = error
        step.completed_at = Database.now_iso()

        # Propagate: find steps that depend on this one and may be blocked
        self._propagate_failure(plan, step_id)

        # Refresh statuses for non-skipped dependents (e.g. completion/always)
        self._refresh_dependent_statuses(plan)

        # Check plan completion
        self._check_plan_completion(plan)

        return step

    def mark_step_running(self, plan: Plan, step_id: str) -> Optional[PlanStep]:
        """Mark a step as running.  Returns the step or *None*."""
        step = self._find_step(plan, step_id)
        if step is None:
            return None
        step.status = StepStatus.RUNNING
        step.started_at = Database.now_iso()
        return step

    def get_plan_progress(self, plan: Plan) -> dict:
        """Return detailed progress information for a plan.

        Includes completed/total counts, current layer, per-status
        breakdown, and whether the plan is finished.
        """
        total = len(plan.steps)
        if total == 0:
            return {
                "plan_id": plan.id,
                "plan_name": plan.name,
                "status": plan.status.value,
                "total_steps": 0,
                "completed": 0,
                "failed": 0,
                "running": 0,
                "ready": 0,
                "pending": 0,
                "skipped": 0,
                "progress_pct": 0.0,
                "current_layer": -1,
                "total_layers": 0,
                "is_finished": plan.status
                in (PlanStatus.COMPLETED, PlanStatus.FAILED, PlanStatus.CANCELLED),
            }

        by_status: dict[str, int] = {}
        for s in plan.steps:
            key = s.status.value
            by_status[key] = by_status.get(key, 0) + 1

        completed = by_status.get("completed", 0)
        failed = by_status.get("failed", 0)
        running = by_status.get("running", 0)
        ready = by_status.get("ready", 0)
        pending = by_status.get("pending", 0)
        skipped = by_status.get("skipped", 0)
        progress_pct = round((completed + failed + skipped) / total * 100, 1)

        # Determine current layer
        try:
            layers = self.get_execution_layers(plan)
        except ValueError:
            layers = []

        current_layer = -1
        for i, layer in enumerate(layers):
            layer_statuses = {
                self._find_step(plan, sid).status
                for sid in layer
                if self._find_step(plan, sid) is not None
            }
            # A layer is "current" if it has running or ready steps
            if layer_statuses & {
                StepStatus.RUNNING,
                StepStatus.READY,
                StepStatus.PENDING,
            }:
                current_layer = i
                break

        return {
            "plan_id": plan.id,
            "plan_name": plan.name,
            "status": plan.status.value,
            "total_steps": total,
            "completed": completed,
            "failed": failed,
            "running": running,
            "ready": ready,
            "pending": pending,
            "skipped": skipped,
            "progress_pct": progress_pct,
            "current_layer": current_layer,
            "total_layers": len(layers),
            "is_finished": plan.status
            in (PlanStatus.COMPLETED, PlanStatus.FAILED, PlanStatus.CANCELLED),
        }

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        """Return planner statistics."""
        return {
            "version": "3.0.0",
            "storage": "sqlite" if self.db else "none",
        }

    # ------------------------------------------------------------------
    # v3.0 Advanced Planner Features
    # ------------------------------------------------------------------

    def score_plan(self, plan: Plan) -> dict:
        """Calculate quality score for a plan (0.0 - 1.0).

        Scoring factors:
        - Parallelization (more layers = lower parallelism score)
        - Dependency complexity
        - Step diversity
        """
        if not plan.steps:
            return {"score": 0.0, "reason": "empty plan"}

        layers = self.get_execution_layers(plan)
        parallelism = len(layers) / max(1, len(plan.steps))  # lower is better parallelism

        # Dependency density
        dep_count = sum(len(s.dependencies) for s in plan.steps)
        dep_density = dep_count / max(1, len(plan.steps))

        # Step type diversity
        types = {s.step_type for s in plan.steps}
        diversity = len(types) / len(VALID_STEP_TYPES)

        # Weighted score
        score = round(
            (1 - parallelism) * 0.4 + (1 - min(dep_density, 1.0)) * 0.35 + diversity * 0.25,
            3,
        )

        return {
            "score": max(0.0, min(1.0, score)),
            "parallelism": round(parallelism, 3),
            "dependency_density": round(dep_density, 3),
            "step_diversity": round(diversity, 3),
            "layers": len(layers),
        }

    def generate_multi_agent_plan(
        self, goal: str, agents: list[str], max_steps_per_agent: int = 4
    ) -> Plan:
        """Generate a simple multi-agent plan skeleton.

        Each agent gets a dedicated 'plan' step + coordination.
        """
        plan = self.create_plan(
            name=f"multi_agent_{goal[:20]}",
            description=f"Multi-agent execution plan for: {goal}",
            goal=goal,
        )

        # Coordination step
        coord = self.add_step(
            plan,
            "plan",
            params={"goal": goal, "mode": "coordination"},
            name="coordination",
        )

        agent_steps = []
        for agent in agents:
            step = self.add_step(
                plan,
                "plan",
                params={"agent_id": agent, "goal": goal},
                name=f"agent_{agent}",
                dependencies=[coord.id],
            )
            agent_steps.append(step)

        # Final aggregation step
        self.add_step(
            plan,
            "reason",
            params={"goal": "aggregate_results"},
            name="aggregation",
            dependencies=[s.id for s in agent_steps],
        )

        plan.status = PlanStatus.PLANNED
        return plan

    # ==================================================================
    # Internal helpers
    # ==================================================================

    def _find_step(self, plan: Plan, step_id: str) -> Optional[PlanStep]:
        """Look up a step by ID within a plan."""
        for s in plan.steps:
            if s.id == step_id:
                return s
        return None

    def _step_label(self, plan: Plan, step_id: str) -> str:
        """Human-readable label for a step (name or id)."""
        step = self._find_step(plan, step_id)
        if step and step.name:
            return f"{step.name} ({step_id[:8]})"
        return step_id[:8]

    def _get_edge_condition(self, plan: Plan, source_id: str, target_id: str) -> str:
        """Get the edge condition between source and target, default 'success'."""
        for e in plan.edges:
            if e.source_id == source_id and e.target_id == target_id:
                return e.condition
        return "success"

    def _dfs_reachable(self, node: str, adj: dict[str, list[str]], visited: set[str]) -> None:
        """Mark all nodes reachable from *node*."""
        stack = [node]
        while stack:
            cur = stack.pop()
            if cur in visited:
                continue
            visited.add(cur)
            for neighbor in adj.get(cur, []):
                if neighbor not in visited:
                    stack.append(neighbor)

    def _has_cycle(self, adj: dict[str, list[str]], nodes: set[str]) -> bool:
        """Return *True* if the graph contains a cycle (DFS 3-coloring)."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {n: WHITE for n in nodes}

        def _dfs(node: str) -> bool:
            color[node] = GRAY
            for nb in adj.get(node, []):
                if color[nb] == GRAY:
                    return True
                if color[nb] == WHITE and _dfs(nb):
                    return True
            color[node] = BLACK
            return False

        return any(color[n] == WHITE and _dfs(n) for n in nodes)

    def _compute_layers_kahn(
        self,
        in_degree: dict[str, int],
        adj: dict[str, list[str]],
    ) -> list[list[str]]:
        """Kahn's algorithm returning layers of parallelisable step IDs."""
        # Work on copies
        in_deg = dict(in_degree)
        layers: list[list[str]] = []

        # Seed with all nodes of in-degree 0
        ready = [sid for sid, deg in in_deg.items() if deg == 0]

        while ready:
            layers.append(sorted(ready))  # sort for determinism
            next_ready: list[str] = []
            for node in ready:
                for neighbor in adj.get(node, []):
                    in_deg[neighbor] -= 1
                    if in_deg[neighbor] == 0:
                        next_ready.append(neighbor)
            ready = next_ready

        return layers

    def _refresh_dependent_statuses(self, plan: Plan) -> None:
        """Update PENDING -> READY for steps whose deps are all completed."""
        completed_ids = {s.id for s in plan.steps if s.status == StepStatus.COMPLETED}
        failed_ids = {s.id for s in plan.steps if s.status == StepStatus.FAILED}

        for step in plan.steps:
            if step.status != StepStatus.PENDING:
                continue
            if not step.dependencies:
                step.status = StepStatus.READY
                continue

            all_satisfied = True
            for dep_id in step.dependencies:
                edge_cond = self._get_edge_condition(plan, dep_id, step.id)
                if edge_cond == "always":
                    continue
                if edge_cond == "success":
                    if dep_id not in completed_ids:
                        all_satisfied = False
                        break
                else:  # completion
                    if dep_id not in completed_ids and dep_id not in failed_ids:
                        all_satisfied = False
                        break

            if all_satisfied:
                step.status = StepStatus.READY

    def _propagate_failure(self, plan: Plan, failed_step_id: str) -> None:
        """Skip dependents whose dependency edge requires success."""
        # Find all steps that directly depend on the failed step
        dependents: list[PlanStep] = []
        for step in plan.steps:
            if failed_step_id in step.dependencies:
                dependents.append(step)

        for dep_step in dependents:
            edge_cond = self._get_edge_condition(plan, failed_step_id, dep_step.id)
            if edge_cond == "success":
                # This dependent can never run — skip it
                if dep_step.status in (StepStatus.PENDING, StepStatus.READY):
                    dep_step.status = StepStatus.SKIPPED
                    dep_step.error = (
                        f"Skipped: dependency '{failed_step_id[:8]}' failed "
                        f"(condition: success)"
                    )
                    # Recursively propagate
                    self._propagate_failure(plan, dep_step.id)

    def _check_plan_completion(self, plan: Plan) -> None:
        """Transition plan status if all steps are terminal."""
        if not plan.steps:
            return
        terminal = {StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED}
        if all(s.status in terminal for s in plan.steps):
            if any(s.status == StepStatus.FAILED for s in plan.steps):
                plan.status = PlanStatus.FAILED
            else:
                plan.status = PlanStatus.COMPLETED

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize_steps(steps: list[PlanStep]) -> list[dict]:
        """Convert a list of PlanStep to JSON-serialisable dicts."""
        result: list[dict] = []
        for s in steps:
            d: dict[str, Any] = {
                "id": s.id,
                "name": s.name,
                "step_type": s.step_type,
                "params": s.params,
                "status": (s.status.value if isinstance(s.status, StepStatus) else s.status),
                "dependencies": s.dependencies,
            }
            if s.result is not None:
                d["result"] = s.result
            if s.error is not None:
                d["error"] = s.error
            if s.started_at is not None:
                d["started_at"] = s.started_at
            if s.completed_at is not None:
                d["completed_at"] = s.completed_at
            if s.constitutional_check is not None:
                d["constitutional_check"] = s.constitutional_check
            result.append(d)
        return result

    @staticmethod
    def _serialize_edges(edges: list[PlanEdge]) -> list[dict]:
        """Convert a list of PlanEdge to JSON-serialisable dicts."""
        return [
            {
                "source_id": e.source_id,
                "target_id": e.target_id,
                "condition": e.condition,
            }
            for e in edges
        ]

    def _deserialize_steps(self, data: list[dict]) -> list[PlanStep]:
        """Convert deserialized dicts back to PlanStep objects."""
        steps: list[PlanStep] = []
        for d in data:
            step = PlanStep(
                id=d["id"],
                name=d.get("name", ""),
                step_type=d.get("step_type", "tool"),
                params=d.get("params", {}),
                status=StepStatus(d.get("status", "pending")),
                dependencies=d.get("dependencies", []),
                result=d.get("result"),
                error=d.get("error"),
                started_at=d.get("started_at"),
                completed_at=d.get("completed_at"),
                constitutional_check=d.get("constitutional_check"),
            )
            steps.append(step)
        return steps

    @staticmethod
    def _deserialize_edges(data: list[dict]) -> list[PlanEdge]:
        """Convert deserialized dicts back to PlanEdge objects."""
        return [
            PlanEdge(
                source_id=e["source_id"],
                target_id=e["target_id"],
                condition=e.get("condition", "success"),
            )
            for e in data
        ]

    def _row_to_plan(self, row: dict) -> Plan:
        """Convert a database row to a Plan object."""
        steps_data = Database.from_json(row["steps_data"]) if row["steps_data"] else []
        edges_data = Database.from_json(row["edges_data"]) if row["edges_data"] else []

        return Plan(
            id=row["id"],
            name=row["name"],
            description=row.get("description", "") or "",
            goal=row.get("goal", "") or "",
            steps=self._deserialize_steps(steps_data),
            edges=self._deserialize_edges(edges_data),
            status=PlanStatus(row["status"]),
            created_at=row["created_at"],
            metadata=Database.from_json(row["metadata"]) if row["metadata"] else {},
        )
