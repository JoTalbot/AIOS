"""Tests for Database Scaling & Multi-backend Storage Abstraction (Milestone 4.2.4)."""


from aios_core.storage import Database


def test_sqlite_storage_basic():
    db = Database(db_path=":memory:")
    assert db.dialect == "sqlite"
    assert db.is_postgres is False

    # Insert test record
    db.execute(
        "INSERT INTO audit_events (id, event_type, data, timestamp, agent_id) VALUES (?, ?, ?, ?, ?)",
        ("audit_100", "task_executed", '{"status": "ok"}', db.now_iso(), "agent_001"),
    )

    rows = db.query("SELECT * FROM audit_events WHERE id = ?", ("audit_100",))
    assert len(rows) == 1
    assert rows[0]["event_type"] == "task_executed"
    assert db.row_count("audit_events") == 1


def test_postgresql_dialect_translation():
    db = Database(db_path="postgresql://user:pass@localhost:5432/aios_db")
    assert db.dialect == "postgresql"
    assert db.is_postgres is True

    # Check parameter translation from ? to %s
    sqlite_query = "SELECT * FROM tasks WHERE status = ? AND agent_id = ?"
    translated = db.translate_query(sqlite_query)
    assert translated == "SELECT * FROM tasks WHERE status = %s AND agent_id = %s"


def test_database_stats_and_tables():
    db = Database(db_path=":memory:")
    stats = db.stats()

    assert stats["schema_version"] == 3
    assert stats["dialect"] == "sqlite"
    assert "audit_events" in stats["tables"]
    assert "tasks" in stats["tables"]
    assert "capabilities" in stats["tables"]
