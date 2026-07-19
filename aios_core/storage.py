"""AIOS Storage Layer v3.0.0

SQLite-based persistence for all AIOS data: audit events, approvals,
memory items, knowledge graph nodes/edges, evolution history.
Provides a unified Database class with automatic schema migration.
"""

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator, Optional

from .config import AIOSConfig, load_config

_SCHEMA_VERSION = 3

_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    data TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    agent_id TEXT,
    decision TEXT,
    tags TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_events(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_agent ON audit_events(agent_id);

CREATE TABLE IF NOT EXISTS approvals (
    id TEXT PRIMARY KEY,
    action_data TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    requested_at TEXT NOT NULL,
    resolved_at TEXT,
    resolved_by TEXT,
    timeout_seconds INTEGER DEFAULT 86400,
    evaluation_id TEXT,
    validation_data TEXT,
    metadata TEXT
);

CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status);
CREATE INDEX IF NOT EXISTS idx_approvals_requested ON approvals(requested_at);

CREATE TABLE IF NOT EXISTS memory_items (
    id TEXT PRIMARY KEY,
    category TEXT NOT NULL DEFAULT 'operational',
    content TEXT NOT NULL,
    tags TEXT,
    source TEXT,
    confidence REAL DEFAULT 1.0,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    expires_at TEXT,
    access_count INTEGER DEFAULT 0,
    metadata TEXT,
    owner_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_memory_category ON memory_items(category);
CREATE INDEX IF NOT EXISTS idx_memory_owner ON memory_items(owner_id);
CREATE INDEX IF NOT EXISTS idx_memory_tags ON memory_items(tags);
CREATE INDEX IF NOT EXISTS idx_memory_created ON memory_items(created_at);

CREATE TABLE IF NOT EXISTS kg_nodes (
    id TEXT PRIMARY KEY,
    node_type TEXT NOT NULL,
    label TEXT NOT NULL,
    properties TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_kg_nodes_type ON kg_nodes(node_type);
CREATE INDEX IF NOT EXISTS idx_kg_nodes_label ON kg_nodes(label);

CREATE TABLE IF NOT EXISTS kg_edges (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES kg_nodes(id),
    target_id TEXT NOT NULL REFERENCES kg_nodes(id),
    relation TEXT NOT NULL,
    properties TEXT,
    weight REAL DEFAULT 1.0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_kg_edges_source ON kg_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_kg_edges_target ON kg_edges(target_id);
CREATE INDEX IF NOT EXISTS idx_kg_edges_relation ON kg_edges(relation);

CREATE TABLE IF NOT EXISTS evolution_records (
    id TEXT PRIMARY KEY,
    evolution_type TEXT NOT NULL,
    previous_state TEXT,
    new_state TEXT,
    reason TEXT,
    expected_result TEXT,
    actual_result TEXT,
    stage TEXT,
    status TEXT DEFAULT 'proposed',
    proposed_at TEXT NOT NULL,
    completed_at TEXT,
    metadata TEXT
);

CREATE INDEX IF NOT EXISTS idx_evo_status ON evolution_records(status);
CREATE INDEX IF NOT EXISTS idx_evo_type ON evolution_records(evolution_type);

CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    data TEXT NOT NULL,
    metadata TEXT,
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);

CREATE TABLE IF NOT EXISTS plans (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    goal TEXT,
    steps_data TEXT,
    edges_data TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL,
    updated_at TEXT,
    metadata TEXT
);

CREATE INDEX IF NOT EXISTS idx_plans_status ON plans(status);
CREATE INDEX IF NOT EXISTS idx_plans_created ON plans(created_at);

CREATE TABLE IF NOT EXISTS capabilities (
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
);

CREATE INDEX IF NOT EXISTS idx_caps_name ON capabilities(name);
CREATE INDEX IF NOT EXISTS idx_caps_status ON capabilities(status);
CREATE INDEX IF NOT EXISTS idx_caps_type ON capabilities(capability_type);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    agent_id TEXT,
    authority TEXT,
    risk_level TEXT DEFAULT 'medium',
    steps_data TEXT,
    current_step_index INTEGER DEFAULT -1,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    error TEXT,
    metadata TEXT
);

CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_agent ON tasks(agent_id);
"""


class Database:
    """Central SQLite database for AIOS persistence.

    Handles connection management, schema migration, and provides
    a context manager for transactions.

    Usage:
        db = Database(":memory:")  # or Database(config)
        with db.transaction() as conn:
            conn.execute("INSERT INTO ...")
    """

    def __init__(self, db_path: Optional[str] = None, config: Optional[AIOSConfig] = None):
        if db_path is not None:
            self.db_path = db_path
        elif config is not None:
            self.db_path = config.resolve_path(config.database.path)
        else:
            config = load_config()
            self.db_path = config.resolve_path(config.database.path)

        self._conn: Optional[sqlite3.Connection] = None
        self._initialize()

    def _initialize(self):
        """Create tables and run migrations."""
        conn = self._get_conn()
        conn.executescript(_CREATE_TABLES)
        conn.commit()
        self._check_migration(conn)

    def _get_conn(self) -> sqlite3.Connection:
        """Get or create the database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def _check_migration(self, conn: sqlite3.Connection):
        """Check and apply schema migrations."""
        row = conn.execute(
            "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
        ).fetchone()

        current = row["version"] if row else 0

        if current < _SCHEMA_VERSION:
            self._migrate(conn, current, _SCHEMA_VERSION)
            conn.execute(
                "INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (?, ?)",
                (_SCHEMA_VERSION, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()

    def _migrate(self, conn: sqlite3.Connection, from_ver: int, to_ver: int):
        """Apply forward-only schema migrations."""
        if from_ver < 2:
            # SQLite does not support ``ADD COLUMN IF NOT EXISTS`` on all
            # supported versions, so inspect the table before altering it.
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(memory_items)")}
            if "owner_id" not in columns:
                conn.execute("ALTER TABLE memory_items ADD COLUMN owner_id TEXT")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memory_owner ON memory_items(owner_id)")
        if from_ver < 3:
            # Tables are created by _CREATE_TABLES, so nothing extra needed
            pass

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for a transactional connection."""
        conn = self._get_conn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a single SQL statement with auto-commit."""
        conn = self._get_conn()
        cursor = conn.execute(sql, params)
        conn.commit()
        return cursor

    def query(self, sql: str, params: tuple = ()) -> list[dict]:
        """Execute a SELECT and return list of dicts."""
        conn = self._get_conn()
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def query_one(self, sql: str, params: tuple = ()) -> Optional[dict]:
        """Execute a SELECT and return a single dict or None."""
        conn = self._get_conn()
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    def close(self):
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # --- Helper methods ---

    @staticmethod
    def new_id() -> str:
        """Generate a new unique ID (UUID hex)."""
        return uuid.uuid4().hex

    @staticmethod
    def now_iso() -> str:
        """Current UTC timestamp in ISO format."""
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def to_json(data: Any) -> str:
        """Serialize data to JSON string."""
        return json.dumps(data, ensure_ascii=False, default=str)

    @staticmethod
    def from_json(json_str: str) -> Any:
        """Deserialize JSON string."""
        return json.loads(json_str)

    def row_count(self, table: str) -> int:
        """Count rows in a table."""
        row = self.query_one(f"SELECT COUNT(*) as cnt FROM {table}")
        return row["cnt"] if row else 0

    def tables(self) -> list[str]:
        """List all tables in the database."""
        rows = self.query(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        return [r["name"] for r in rows]

    def stats(self) -> dict:
        """Return database statistics."""
        return {
            "db_path": self.db_path,
            "schema_version": _SCHEMA_VERSION,
            "tables": {
                "audit_events": self.row_count("audit_events"),
                "approvals": self.row_count("approvals"),
                "memory_items": self.row_count("memory_items"),
                "kg_nodes": self.row_count("kg_nodes"),
                "kg_edges": self.row_count("kg_edges"),
                "evolution_records": self.row_count("evolution_records"),
                "events": self.row_count("events"),
                "plans": self.row_count("plans"),
                "capabilities": self.row_count("capabilities"),
                "tasks": self.row_count("tasks"),
            },
        }