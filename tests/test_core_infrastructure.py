"""Tests for Storage, Tracer, Telemetry — core infrastructure."""

from aios_core.storage import Database


def test_database_creates_tables():
    db = Database(":memory:")
    tables = db.tables()
    assert isinstance(tables, list)  # empty but valid


def test_database_new_id():
    uid = Database.new_id()
    assert len(uid) == 32  # uuid hex


def test_database_now_iso():
    ts = Database.now_iso()
    assert "T" in ts  # ISO format


def test_database_to_json():
    j = Database.to_json({"key": "val"})
    assert '"key"' in j


def test_database_from_json():
    d = Database.from_json('{"a": 1}')
    assert d["a"] == 1


def test_database_stats():
    db = Database(":memory:")
    s = db.stats()
    assert "dialect" in s
    assert s["dialect"] in ("sqlite", "postgresql")
