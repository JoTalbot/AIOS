"""Tests for aios_core/storage.py"""
from __future__ import annotations
import pytest
from aios_core.storage import Database


@pytest.fixture()
def db(tmp_path):
    db = Database(db_path=str(tmp_path / "test.db"))
    yield db
    db.close()


class TestDatabase:
    def test_create(self, db):
        assert db is not None

    def test_execute(self, db):
        db.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, name TEXT)")
        db.execute("INSERT INTO test (name) VALUES (?)", ("hello",))

    def test_query(self, db):
        db.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, name TEXT)")
        db.execute("INSERT INTO test (name) VALUES (?)", ("hello",))
        rows = db.query("SELECT * FROM test")
        assert isinstance(rows, list)
        assert len(rows) >= 1

    def test_query_one(self, db):
        db.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, name TEXT)")
        db.execute("INSERT INTO test (name) VALUES (?)", ("hello",))
        row = db.query_one("SELECT * FROM test")
        assert row is not None

    def test_transaction(self, db):
        db.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY, name TEXT)")
        with db.transaction():
            db.execute("INSERT INTO test (name) VALUES (?)", ("tx1",))
            db.execute("INSERT INTO test (name) VALUES (?)", ("tx2",))
        rows = db.query("SELECT * FROM test")
        assert len(rows) >= 2

    def test_close(self, db):
        db.close()
