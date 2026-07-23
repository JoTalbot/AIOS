"""AIOS Capability Engine v3.0.0

Discoverable, composable capability registry with lifecycle management.

Lifecycle states:
    discovered -> registered -> tested -> validated -> trusted -> optimized -> deprecated -> retired

Capabilities are persisted to SQLite while handlers (callables) are kept
in-memory only and must be re-registered after a system restart.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Optional

from .storage import Database

# ---------------------------------------------------------------------------
# Status enum
# ---------------------------------------------------------------------------


class CapabilityStatus(Enum):
    """Lifecycle states for a capability."""

    DISCOVERED = "discovered"
    REGISTERED = "registered"
    TESTING = "testing"
    TESTED = "tested"
    VALIDATED = "validated"
    TRUSTED = "trusted"
    OPTIMIZED = "optimized"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


# ---------------------------------------------------------------------------
# Allowed transitions  (from_status -> set of valid to_statuses)
# "Any -> retired" is handled separately as an emergency override.
# ---------------------------------------------------------------------------

_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "discovered": {"registered"},
    "registered": {"testing", "deprecated"},
    "testing": {"tested", "registered"},
    "tested": {"validated", "testing"},
    "validated": {"trusted", "tested"},
    "trusted": {"optimized", "validated", "deprecated"},
    "optimized": {"trusted", "deprecated"},
    "deprecated": {"retired"},
    "retired": set(),
}

# Statuses that are considered usable for execution (at least registered)
_EXECUTABLE_STATUSES = {
    CapabilityStatus.REGISTERED.value,
    CapabilityStatus.TESTING.value,
    CapabilityStatus.TESTED.value,
    CapabilityStatus.VALIDATED.value,
    CapabilityStatus.TRUSTED.value,
    CapabilityStatus.OPTIMIZED.value,
}

# Authority hierarchy — higher index = greater authority
_AUTHORITY_LEVELS: list[str] = ["user", "agent", "system", "admin", "root"]

# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------


@dataclass
class Capability:
    """Represents a single capability in the registry."""

    id: str
    name: str
    description: str
    capability_type: str
    status: CapabilityStatus
    version: str = "1.0.0"
    handler: Optional[Callable] = None
    input_schema: Optional[dict] = None
    output_schema: Optional[dict] = None
    risk_level: str = "low"
    required_authority: str = "user"
    tags: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    properties: dict = field(default_factory=dict)
    registered_at: str = ""
    updated_at: Optional[str] = None
    validated_at: Optional[str] = None
    deprecated_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Capability Engine
# ---------------------------------------------------------------------------


class CapabilityEngine:
    """Discoverable, composable capability registry with lifecycle management.

    v3.0.0: Full lifecycle pipeline with SQLite persistence and in-memory
    handler storage.  Handlers must be re-registered after a restart.
    """

    def __init__(self, db: Optional[Database] = None):
        self.db = db
        self.version = "3.0.0"
        self._handlers: dict[str, Callable] = {}
        self._in_memory: dict[str, dict] = {}
        self._create_table()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _create_table(self) -> None:
        """Create the capabilities table if it does not exist."""
        if self.db is None:
            return
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS capabilities (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                capability_type TEXT NOT NULL,
                status TEXT NOT NULL,
                version TEXT DEFAULT '1.0.0',
                input_schema TEXT,
                output_schema TEXT,
                risk_level TEXT DEFAULT 'low',
                required_authority TEXT DEFAULT 'user',
                tags TEXT,
                dependencies TEXT,
                metrics TEXT,
                properties TEXT,
                registered_at TEXT NOT NULL,
                updated_at TEXT,
                validated_at TEXT,
                deprecated_at TEXT
            )""",
        )
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_cap_name ON capabilities(name)",
        )
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_cap_status ON capabilities(status)",
        )
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_cap_type ON capabilities(capability_type)",
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _serialize_capability(self, cap: Capability) -> dict:
        """Convert a Capability dataclass to a plain dict (without handler)."""
        return {
            "id": cap.id,
            "name": cap.name,
            "description": cap.description,
            "capability_type": cap.capability_type,
            "status": cap.status.value,
            "version": cap.version,
            "input_schema": cap.input_schema,
            "output_schema": cap.output_schema,
            "risk_level": cap.risk_level,
            "required_authority": cap.required_authority,
            "tags": cap.tags,
            "dependencies": cap.dependencies,
            "metrics": cap.metrics,
            "properties": cap.properties,
            "registered_at": cap.registered_at,
            "updated_at": cap.updated_at,
            "validated_at": cap.validated_at,
            "deprecated_at": cap.deprecated_at,
        }

    def _persist(self, cap: Capability) -> None:
        """Insert or update a capability in SQLite (and in-memory fallback)."""
        data = self._serialize_capability(cap)
        self._in_memory[cap.name] = dict(data)
        if self.db is None:
            return
        # data is already built above
        self.db.execute(
            """INSERT INTO capabilities
                   (id, name, description, capability_type, status, version,
                    input_schema, output_schema, risk_level, required_authority,
                    tags, dependencies, metrics, properties,
                    registered_at, updated_at, validated_at, deprecated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(name) DO UPDATE SET
                    description=excluded.description,
                    capability_type=excluded.capability_type,
                    status=excluded.status,
                    version=excluded.version,
                    input_schema=excluded.input_schema,
                    output_schema=excluded.output_schema,
                    risk_level=excluded.risk_level,
                    required_authority=excluded.required_authority,
                    tags=excluded.tags,
                    dependencies=excluded.dependencies,
                    metrics=excluded.metrics,
                    properties=excluded.properties,
                    updated_at=excluded.updated_at,
                    validated_at=excluded.validated_at,
                    deprecated_at=excluded.deprecated_at""",
            (
                data["id"],
                data["name"],
                data["description"],
                data["capability_type"],
                data["status"],
                data["version"],
                _json(data["input_schema"]),
                _json(data["output_schema"]),
                data["risk_level"],
                data["required_authority"],
                _json(data["tags"]),
                _json(data["dependencies"]),
                _json(data["metrics"]),
                _json(data["properties"]),
                data["registered_at"],
                data["updated_at"],
                data["validated_at"],
                data["deprecated_at"],
            ),
        )

    def _load_from_db(self, name: str) -> Optional[dict]:
        """Load a single capability row from SQLite or in-memory fallback."""
        if self.db is None:
            return self._in_memory.get(name)
        row = self.db.query_one("SELECT * FROM capabilities WHERE name = ?", (name,))
        if row is None:
            return None
        return self._row_to_dict(row)

    def _row_to_dict(self, row: dict) -> dict:
        """Convert a DB row to a capability dict with parsed JSON fields."""
        return {
            "id": row["id"],
            "name": row["name"],
            "description": row["description"],
            "capability_type": row["capability_type"],
            "status": row["status"],
            "version": row["version"],
            "input_schema": (
                Database.from_json(row["input_schema"]) if row.get("input_schema") else None
            ),
            "output_schema": (
                Database.from_json(row["output_schema"]) if row.get("output_schema") else None
            ),
            "risk_level": row["risk_level"],
            "required_authority": row["required_authority"],
            "tags": Database.from_json(row["tags"]) if row.get("tags") else [],
            "dependencies": (
                Database.from_json(row["dependencies"]) if row.get("dependencies") else []
            ),
            "metrics": (
                Database.from_json(row["metrics"])
                if row.get("metrics")
                else {
                    "execution_count": 0,
                    "success_count": 0,
                    "failure_count": 0,
                    "avg_duration_ms": 0.0,
                    "last_executed": None,
                }
            ),
            "properties": (Database.from_json(row["properties"]) if row.get("properties") else {}),
            "registered_at": row["registered_at"],
            "updated_at": row["updated_at"],
            "validated_at": row["validated_at"],
            "deprecated_at": row["deprecated_at"],
        }

    def _update_field(self, name: str, **fields: Any) -> bool:
        """Update arbitrary fields on an existing capability row."""
        if not fields:
            return False
        # Always update in-memory fallback
        if name in self._in_memory:
            self._in_memory[name].update(fields)
        if self.db is None:
            return name in self._in_memory
        set_parts = [f"{k} = ?" for k in fields]
        values = list(fields.values()) + [name]
        cursor = self.db.execute(
            f"UPDATE capabilities SET {', '.join(set_parts)} WHERE name = ?",
            tuple(values),
        )
        return cursor.rowcount > 0

    def _audit(self, event_type: str, data: dict) -> None:
        """Write an audit event (best-effort, same table as audit_logger)."""
        if self.db is None:
            return
        try:
            self.db.execute(
                """INSERT INTO audit_events
                       (id, event_type, data, timestamp)
                   VALUES (?, ?, ?, ?)""",
                (
                    Database.new_id(),
                    event_type,
                    Database.to_json(data),
                    Database.now_iso(),
                ),
            )
        except Exception:
            # Audit logging must never break the caller.
            pass

    @staticmethod
    def _authority_sufficient(provided: str, required: str) -> bool:
        """Return True if *provided* authority meets or exceeds *required*."""
        try:
            return _AUTHORITY_LEVELS.index(provided) >= _AUTHORITY_LEVELS.index(required)
        except ValueError:
            return False

    # ------------------------------------------------------------------
    # Public API — Registration
    # ------------------------------------------------------------------

    def register(
        self,
        name: str,
        description: str,
        handler: Optional[Callable] = None,
        capability_type: str = "tool",
        input_schema: Optional[dict] = None,
        output_schema: Optional[dict] = None,
        risk_level: str = "low",
        required_authority: str = "user",
        tags: Optional[list[str]] = None,
        dependencies: Optional[list[str]] = None,
        properties: Optional[dict] = None,
    ) -> dict:
        """Register a new capability with status ``registered``.

        Returns the capability dict as stored.
        """
        now = Database.now_iso()
        cap_id = Database.new_id()

        cap = Capability(
            id=cap_id,
            name=name,
            description=description,
            capability_type=capability_type,
            status=CapabilityStatus.REGISTERED,
            version="1.0.0",
            handler=handler,
            input_schema=input_schema,
            output_schema=output_schema,
            risk_level=risk_level,
            required_authority=required_authority,
            tags=tags or [],
            dependencies=dependencies or [],
            metrics={
                "execution_count": 0,
                "success_count": 0,
                "failure_count": 0,
                "avg_duration_ms": 0.0,
                "last_executed": None,
            },
            properties=properties or {},
            registered_at=now,
        )

        # Store handler in memory
        if handler is not None:
            self._handlers[name] = handler

        self._persist(cap)

        result = self._serialize_capability(cap)
        self._audit("capability_registered", result)
        return result

    def discover(
        self,
        name: str,
        description: str,
        capability_type: str = "tool",
        properties: Optional[dict] = None,
    ) -> dict:
        """Register a capability as *discovered* (not yet ready for use)."""
        now = Database.now_iso()
        cap_id = Database.new_id()

        cap = Capability(
            id=cap_id,
            name=name,
            description=description,
            capability_type=capability_type,
            status=CapabilityStatus.DISCOVERED,
            version="1.0.0",
            tags=[],
            dependencies=[],
            metrics={
                "execution_count": 0,
                "success_count": 0,
                "failure_count": 0,
                "avg_duration_ms": 0.0,
                "last_executed": None,
            },
            properties=properties or {},
            registered_at=now,
        )

        self._persist(cap)

        result = self._serialize_capability(cap)
        self._audit("capability_discovered", result)
        return result

    # ------------------------------------------------------------------
    # Public API — Execution
    # ------------------------------------------------------------------

    def execute(
        self,
        capability_name: str,
        input_data: dict,
        agent_id: str = "system",
        authority: str = "system",
    ) -> dict:
        """Execute a capability by name.

        Checks status and authority, records metrics, invokes the handler,
        and returns a structured result dict.
        """
        cap_data = self.get_capability(capability_name)
        if cap_data is None:
            return {
                "success": False,
                "result": None,
                "capability": capability_name,
                "duration_ms": 0.0,
                "error": f"Capability '{capability_name}' not found",
            }

        status = cap_data["status"]

        # Check status
        if status not in _EXECUTABLE_STATUSES:
            return {
                "success": False,
                "result": None,
                "capability": capability_name,
                "duration_ms": 0.0,
                "error": (
                    f"Capability '{capability_name}' is in status '{status}' "
                    f"and cannot be executed"
                ),
            }

        # Check authority
        required_auth = cap_data.get("required_authority", "user")
        if not self._authority_sufficient(authority, required_auth):
            return {
                "success": False,
                "result": None,
                "capability": capability_name,
                "duration_ms": 0.0,
                "error": (f"Authority '{authority}' insufficient; " f"requires '{required_auth}'"),
            }

        # Check handler availability
        handler = self._handlers.get(capability_name)
        if handler is None:
            return {
                "success": False,
                "result": None,
                "capability": capability_name,
                "duration_ms": 0.0,
                "error": (
                    f"No handler registered for '{capability_name}'. "
                    f"Handlers must be re-registered after a system restart."
                ),
            }

        # Execute with timing
        metrics = cap_data.get("metrics", {})
        exec_count = metrics.get("execution_count", 0)
        success_count = metrics.get("success_count", 0)
        failure_count = metrics.get("failure_count", 0)
        avg_duration = metrics.get("avg_duration_ms", 0.0)

        t0 = time.monotonic()
        try:
            result = handler(input_data)
            elapsed_ms = (time.monotonic() - t0) * 1000.0
            success = True
            success_count += 1
            error = None
        except Exception as exc:
            elapsed_ms = (time.monotonic() - t0) * 1000.0
            success = False
            result = None
            error = str(exc)
            failure_count += 1

        exec_count += 1
        # Rolling average
        if exec_count > 0:
            avg_duration = ((avg_duration * (exec_count - 1)) + elapsed_ms) / exec_count

        updated_metrics = {
            "execution_count": exec_count,
            "success_count": success_count,
            "failure_count": failure_count,
            "avg_duration_ms": round(avg_duration, 3),
            "last_executed": Database.now_iso(),
        }

        # Persist updated metrics (dict in-memory, JSON in DB)
        if self.db is not None:
            self._update_field(capability_name, metrics=_json(updated_metrics))
        elif capability_name in self._in_memory:
            self._in_memory[capability_name]["metrics"] = updated_metrics

        self._audit(
            "capability_executed",
            {
                "capability": capability_name,
                "agent_id": agent_id,
                "authority": authority,
                "success": success,
                "duration_ms": round(elapsed_ms, 3),
                "error": error,
            },
        )

        return {
            "success": success,
            "result": result,
            "capability": capability_name,
            "duration_ms": round(elapsed_ms, 3),
            "error": error,
        }

    # ------------------------------------------------------------------
    # Public API — Lifecycle transitions
    # ------------------------------------------------------------------

    def transition(
        self,
        capability_name: str,
        new_status: str,
        reason: str = "",
    ) -> dict:
        """Move a capability through its lifecycle.

        Validates the transition is allowed and records an audit event.
        Emergency retirement (any -> retired) is always permitted.
        """
        cap_data = self.get_capability(capability_name)
        if cap_data is None:
            return {
                "success": False,
                "capability": capability_name,
                "old_status": None,
                "new_status": new_status,
                "error": f"Capability '{capability_name}' not found",
            }

        old_status = cap_data["status"]
        now = Database.now_iso()

        # Validate the new status value
        valid_values = {s.value for s in CapabilityStatus}
        if new_status not in valid_values:
            return {
                "success": False,
                "capability": capability_name,
                "old_status": old_status,
                "new_status": new_status,
                "error": (
                    f"Invalid status '{new_status}'. " f"Must be one of: {sorted(valid_values)}"
                ),
            }

        # Same status is a no-op
        if old_status == new_status:
            return {
                "success": True,
                "capability": capability_name,
                "old_status": old_status,
                "new_status": new_status,
                "reason": reason or "No change (status already set)",
            }

        # Emergency retirement from any state
        if new_status == "retired":
            self._update_field(
                capability_name,
                status="retired",
                updated_at=now,
                deprecated_at=cap_data.get("deprecated_at") or now,
            )
            self._audit(
                "capability_transition",
                {
                    "capability": capability_name,
                    "old_status": old_status,
                    "new_status": "retired",
                    "reason": reason or "Emergency retirement",
                },
            )
            return {
                "success": True,
                "capability": capability_name,
                "old_status": old_status,
                "new_status": "retired",
                "reason": reason or "Emergency retirement",
            }

        # Normal transition check
        allowed = _ALLOWED_TRANSITIONS.get(old_status, set())
        if new_status not in allowed:
            return {
                "success": False,
                "capability": capability_name,
                "old_status": old_status,
                "new_status": new_status,
                "error": (
                    f"Transition from '{old_status}' to '{new_status}' "
                    f"is not allowed. Allowed: {sorted(allowed)}"
                ),
            }

        # Apply the transition
        update_fields: dict[str, Any] = {
            "status": new_status,
            "updated_at": now,
        }

        # Set validated_at when entering validated
        if new_status == "validated":
            update_fields["validated_at"] = now

        # Set deprecated_at when entering deprecated
        if new_status == "deprecated":
            update_fields["deprecated_at"] = now

        self._update_field(capability_name, **update_fields)

        self._audit(
            "capability_transition",
            {
                "capability": capability_name,
                "old_status": old_status,
                "new_status": new_status,
                "reason": reason,
            },
        )

        return {
            "success": True,
            "capability": capability_name,
            "old_status": old_status,
            "new_status": new_status,
            "reason": reason,
        }

    # ------------------------------------------------------------------
    # Public API — Composition
    # ------------------------------------------------------------------

    def compose(
        self,
        composition_name: str,
        capabilities: list[dict],
        description: str = "",
    ) -> dict:
        """Create a composite capability from a sequence of capabilities.

        Each element in *capabilities* is a dict with:
            - ``name`` (str): name of an existing capability
            - ``mapping`` (dict): maps output keys to the next capability's
              input keys.  Empty dict means the full output is passed
              as ``input_data``.

        The composed handler executes capabilities in order, threading
        mapped outputs as inputs to the next step.
        """
        if not capabilities:
            return {
                "success": False,
                "composition": composition_name,
                "error": "capabilities list must not be empty",
            }

        # Validate that all referenced capabilities exist
        step_caps: list[dict] = []
        for step in capabilities:
            step_name = step.get("name", "")
            cap_data = self.get_capability(step_name)
            if cap_data is None:
                return {
                    "success": False,
                    "composition": composition_name,
                    "error": f"Step capability '{step_name}' not found",
                }
            step_caps.append(
                {
                    "name": step_name,
                    "mapping": step.get("mapping", {}),
                    "capability": cap_data,
                }
            )

        # Build the composed handler
        engine_self = self  # capture for closure

        def composed_handler(input_data: dict) -> Any:
            """Execute the composition pipeline."""
            current = dict(input_data)
            last_result = None
            for step in step_caps:
                step_name = step["name"]
                mapping = step["mapping"]
                # Apply mapping: pick/rename keys from current into next input
                if mapping:
                    next_input = {}
                    for src_key, dst_key in mapping.items():
                        if src_key in current:
                            next_input[dst_key] = current[src_key]
                else:
                    next_input = dict(current)
                resp = engine_self.execute(step_name, next_input, authority="system")
                if not resp["success"]:
                    raise RuntimeError(
                        f"Composition step '{step_name}' failed: "
                        f"{resp.get('error', 'unknown error')}"
                    )
                last_result = resp["result"]
                # Merge result into current context for next step
                if isinstance(last_result, dict):
                    current.update(last_result)
            return last_result

        # Register the composition as a new capability
        dep_names = [s["name"] for s in step_caps]
        full_desc = description or (f"Composite capability chaining: " f"{' -> '.join(dep_names)}")

        result = self.register(
            name=composition_name,
            description=full_desc,
            handler=composed_handler,
            capability_type="composition",
            dependencies=dep_names,
            properties={
                "composition_steps": capabilities,
                "step_count": len(capabilities),
            },
        )

        self._audit(
            "capability_composed",
            {
                "composition": composition_name,
                "steps": dep_names,
            },
        )

        return {
            "success": True,
            "composition": composition_name,
            "capability": result,
        }

    # ------------------------------------------------------------------
    # Public API — Search / Query
    # ------------------------------------------------------------------

    def search(
        self,
        query: Optional[str] = None,
        capability_type: Optional[str] = None,
        status: Optional[str] = None,
        tag: Optional[str] = None,
        risk_level: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """Search / filter capabilities."""
        if self.db is None:
            # In-memory fallback
            results = list(self._in_memory.values())
            if query:
                q = query.lower()
                results = [
                    c
                    for c in results
                    if q in c.get("name", "").lower() or q in c.get("description", "").lower()
                ]
            if capability_type:
                results = [c for c in results if c.get("capability_type") == capability_type]
            if status:
                results = [c for c in results if c.get("status") == status]
            if tag:
                results = [c for c in results if tag in c.get("tags", [])]
            if risk_level:
                results = [c for c in results if c.get("risk_level") == risk_level]
            results.sort(key=lambda c: c.get("registered_at", ""), reverse=True)
            return results[:limit]

        conditions: list[str] = []
        params: list[Any] = []

        if query:
            conditions.append("(name LIKE ? OR description LIKE ? OR properties LIKE ?)")
            like = f"%{query}%"
            params.extend([like, like, like])

        if capability_type:
            conditions.append("capability_type = ?")
            params.append(capability_type)

        if status:
            conditions.append("status = ?")
            params.append(status)

        if tag:
            conditions.append("(tags IS NOT NULL AND tags LIKE ?)")
            params.append(f"%{tag}%")

        if risk_level:
            conditions.append("risk_level = ?")
            params.append(risk_level)

        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)

        sql = f"SELECT * FROM capabilities {where} ORDER BY registered_at DESC LIMIT ?"
        params.append(limit)

        rows = self.db.query(sql, tuple(params))
        return [self._row_to_dict(r) for r in rows]

    def get_capability(self, name: str) -> Optional[dict]:
        """Retrieve a single capability by name."""
        return self._load_from_db(name)

    # ------------------------------------------------------------------
    # Public API — Deprecate / Retire
    # ------------------------------------------------------------------

    def deprecate(self, name: str, reason: str = "") -> dict:
        """Mark a capability as deprecated."""
        return self.transition(name, "deprecated", reason=reason or "Deprecated")

    def retire(self, name: str, reason: str = "") -> dict:
        """Mark a capability as retired (unusable)."""
        return self.transition(name, "retired", reason=reason or "Retired")

    # ------------------------------------------------------------------
    # Public API — Stats
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        """Return capability engine statistics."""
        if self.db is None:
            by_status: dict[str, int] = {}
            by_type: dict[str, int] = {}
            for cap in self._in_memory.values():
                s = cap.get("status", "unknown")
                by_status[s] = by_status.get(s, 0) + 1
                t = cap.get("capability_type", "unknown")
                by_type[t] = by_type.get(t, 0) + 1
            return {
                "version": self.version,
                "total_capabilities": len(self._in_memory),
                "by_status": by_status,
                "by_type": by_type,
                "handlers_loaded": len(self._handlers),
                "storage": "none",
            }

        total_row = self.db.query_one("SELECT COUNT(*) as cnt FROM capabilities")
        total = total_row["cnt"] if total_row else 0

        by_status_rows = self.db.query(
            "SELECT status, COUNT(*) as cnt FROM capabilities GROUP BY status"
        )
        by_status = {r["status"]: r["cnt"] for r in by_status_rows}

        by_type_rows = self.db.query(
            "SELECT capability_type, COUNT(*) as cnt FROM capabilities " "GROUP BY capability_type"
        )
        by_type = {r["capability_type"]: r["cnt"] for r in by_type_rows}

        return {
            "version": self.version,
            "total_capabilities": total,
            "by_status": by_status,
            "by_type": by_type,
            "handlers_loaded": len(self._handlers),
            "storage": "sqlite",
        }

    # ------------------------------------------------------------------
    # v3.0 Dynamic capabilities — auto-suggestion
    # ------------------------------------------------------------------

    def suggest_capabilities(self, limit: int = 5) -> list[dict]:
        """Suggest new capabilities based on execution patterns and gaps.

        Heuristics:
        - High-frequency capabilities that are still in early status
        - Capabilities with many failures (suggest improvement)
        - Missing common types (reasoning, memory, knowledge)
        """
        suggestions = []

        # Get top executed capabilities
        if self.db:
            top = self.db.query(
                """SELECT name, capability_type, metrics, status
                   FROM capabilities
                   ORDER BY json_extract(metrics, '$.execution_count') DESC
                   LIMIT ?""",
                (limit + 3,),
            )
        else:
            top = sorted(
                self._in_memory.values(),
                key=lambda c: c.get("metrics", {}).get("execution_count", 0),
                reverse=True,
            )[: limit + 3]

        for cap in top:
            metrics = cap.get("metrics", {}) if isinstance(cap, dict) else {}
            exec_count = metrics.get("execution_count", 0) if isinstance(metrics, dict) else 0
            failure_rate = 0
            if exec_count > 0:
                failures = metrics.get("failure_count", 0)
                failure_rate = failures / exec_count

            # Suggest improvement if high failure rate
            if failure_rate > 0.3:
                suggestions.append(
                    {
                        "name": f"improved_{cap.get('name', 'unknown')}",
                        "description": f"Improved version of {cap.get('name')} (high failure rate)",
                        "capability_type": cap.get("capability_type", "tool"),
                        "reason": "high_failure_rate",
                        "confidence": round(1 - failure_rate, 2),
                    }
                )

            # Suggest optimization for trusted capabilities with high usage
            if cap.get("status") in ("trusted", "optimized") and exec_count > 100:
                suggestions.append(
                    {
                        "name": f"optimized_{cap.get('name', 'unknown')}",
                        "description": f"Optimized variant of heavily used capability",
                        "capability_type": "optimization",
                        "reason": "high_usage",
                        "confidence": 0.85,
                    }
                )

        # Add generic suggestions for missing core types
        existing_types = {
            c.get("capability_type") for c in (self._in_memory.values() if not self.db else [])
        }
        for missing in ["reasoning", "memory", "knowledge", "evolution"]:
            if missing not in existing_types:
                suggestions.append(
                    {
                        "name": f"core_{missing}",
                        "description": f"Core {missing} capability (auto-suggested)",
                        "capability_type": missing,
                        "reason": "missing_core_type",
                        "confidence": 0.9,
                    }
                )

        return suggestions[:limit]


# ---------------------------------------------------------------------------
# Module-level helper
# ---------------------------------------------------------------------------


def _json(data: Any) -> Optional[str]:
    """Serialize to JSON, returning None for None input."""
    if data is None:
        return None
    return Database.to_json(data)
