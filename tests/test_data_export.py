"""Tests for AIOS data export/import utilities."""

import csv
import json
import sqlite3

import pytest

from aios_core.data_export import DataExporter, DataImporter


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary test database."""
    db_path = tmp_path / "test.sqlite"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """
        CREATE TABLE tasks (
            id TEXT PRIMARY KEY,
            status TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """
    )
    conn.execute(
        """
        CREATE TABLE personal_memory (
            id TEXT PRIMARY KEY,
            owner TEXT,
            content TEXT,
            created_at TEXT
        )
    """
    )
    conn.execute(
        """
        CREATE TABLE audit_log (
            id TEXT PRIMARY KEY,
            event_type TEXT,
            timestamp TEXT,
            details TEXT
        )
    """
    )
    conn.execute(
        """
        CREATE TABLE knowledge_graph (
            id TEXT PRIMARY KEY,
            subject TEXT,
            predicate TEXT,
            object TEXT,
            created_at TEXT
        )
    """
    )
    # Insert test data
    conn.execute("INSERT INTO tasks VALUES ('task-1', 'completed', '2026-01-01', '2026-01-02')")
    conn.execute("INSERT INTO tasks VALUES ('task-2', 'running', '2026-07-01', '2026-07-02')")
    conn.execute(
        "INSERT INTO personal_memory VALUES ('mem-1', 'user1', 'test content', '2026-01-01')"
    )
    conn.execute("INSERT INTO audit_log VALUES ('log-1', 'task.create', '2026-07-20', '{}')")
    conn.execute(
        "INSERT INTO knowledge_graph VALUES ('kg-1', 'AIOS', 'is', 'awesome', '2026-01-01')"
    )
    conn.commit()
    conn.close()
    return str(db_path)


class TestDataExporter:
    def test_export_tasks_json(self, temp_db, tmp_path):
        output = tmp_path / "tasks.json"
        with DataExporter(temp_db) as exporter:
            count = exporter.export_tasks(str(output), format="json")
        assert count == 2
        with open(output) as f:
            data = json.load(f)
        assert data["count"] == 2
        assert len(data["data"]) == 2

    def test_export_tasks_csv(self, temp_db, tmp_path):
        output = tmp_path / "tasks.csv"
        with DataExporter(temp_db) as exporter:
            count = exporter.export_tasks(str(output), format="csv")
        assert count == 2
        with open(output) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 2

    def test_export_tasks_with_filter(self, temp_db, tmp_path):
        output = tmp_path / "tasks.json"
        with DataExporter(temp_db) as exporter:
            count = exporter.export_tasks(str(output), format="json", status="completed")
        assert count == 1

    def test_export_tasks_with_limit(self, temp_db, tmp_path):
        output = tmp_path / "tasks.json"
        with DataExporter(temp_db) as exporter:
            count = exporter.export_tasks(str(output), format="json", limit=1)
        assert count == 1

    def test_export_memory(self, temp_db, tmp_path):
        output = tmp_path / "memory.json"
        with DataExporter(temp_db) as exporter:
            count = exporter.export_memory(str(output), format="json")
        assert count == 1

    def test_export_audit_log(self, temp_db, tmp_path):
        output = tmp_path / "audit.json"
        with DataExporter(temp_db) as exporter:
            count = exporter.export_audit_log(str(output), format="json")
        assert count == 1

    def test_export_knowledge_graph(self, temp_db, tmp_path):
        output = tmp_path / "kg.json"
        with DataExporter(temp_db) as exporter:
            count = exporter.export_knowledge_graph(str(output), format="json")
        assert count == 1

    def test_export_all(self, temp_db, tmp_path):
        output_dir = tmp_path / "export"
        with DataExporter(temp_db) as exporter:
            counts = exporter.export_all(str(output_dir), format="json")
        assert counts["tasks"] == 2
        assert counts["memory"] == 1
        assert counts["audit"] == 1
        assert counts["knowledge"] == 1

    def test_export_invalid_format(self, temp_db, tmp_path):
        output = tmp_path / "tasks.xml"
        with DataExporter(temp_db) as exporter:
            with pytest.raises(ValueError, match="Unsupported format"):
                exporter.export_tasks(str(output), format="xml")


class TestDataImporter:
    def test_import_tasks_json(self, temp_db, tmp_path):
        # First export
        json_file = tmp_path / "tasks.json"
        with DataExporter(temp_db) as exporter:
            exporter.export_tasks(str(json_file), format="json")

        # Create new db
        new_db = tmp_path / "new.sqlite"
        conn = sqlite3.connect(str(new_db))
        conn.execute(
            "CREATE TABLE tasks (id TEXT PRIMARY KEY, status TEXT, created_at TEXT, updated_at TEXT)"
        )
        conn.commit()
        conn.close()

        # Import
        with DataImporter(str(new_db)) as importer:
            count = importer.import_tasks(str(json_file), format="json")
        assert count == 2

    def test_import_tasks_csv(self, temp_db, tmp_path):
        csv_file = tmp_path / "tasks.csv"
        with DataExporter(temp_db) as exporter:
            exporter.export_tasks(str(csv_file), format="csv")

        new_db = tmp_path / "new.sqlite"
        conn = sqlite3.connect(str(new_db))
        conn.execute(
            "CREATE TABLE tasks (id TEXT PRIMARY KEY, status TEXT, created_at TEXT, updated_at TEXT)"
        )
        conn.commit()
        conn.close()

        with DataImporter(str(new_db)) as importer:
            count = importer.import_tasks(str(csv_file), format="csv")
        assert count == 2
