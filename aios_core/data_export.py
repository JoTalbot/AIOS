"""Data Export/Import utilities for AIOS

Provides export and import functionality for:
- Tasks and execution history
- Memory records
- Knowledge graph entries
- Evolution records
- Audit logs

Formats: JSON, CSV, SQLite dump
"""

import csv
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional


class DataExporter:
    """Export AIOS data to various formats."""

    def __init__(self, db_path: str = "aios.sqlite") -> None:
        self.db_path = db_path
        self.conn = None

    def connect(self) -> None:
        """Connect to database."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self) -> None:
        self.connect()
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def _table_columns(self, table: str) -> set[str]:
        """Return columns for an optional table without failing an export."""
        row = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if not row:
            return set()
        return {item[1] for item in self.conn.execute(f"PRAGMA table_info({table})")}

    def export_tasks(
        self,
        output_path: str,
        format: str = "json",
        limit: Optional[int] = None,
        status: Optional[str] = None,
        since: Optional[str] = None,
    ) -> int:
        """Export tasks to file.

        Args:
            output_path: Path to output file
            format: 'json' or 'csv'
            limit: Maximum number of records
            status: Filter by status (completed, failed, running)
            since: ISO date string (e.g. '2026-01-01')

        Returns:
            Number of records exported
        """
        columns = self._table_columns("tasks")
        params = []
        if not columns:
            rows = []
        else:
            query = "SELECT * FROM tasks WHERE 1=1"
            if status and "status" in columns:
                query += " AND status = ?"
                params.append(status)
            if since and "created_at" in columns:
                query += " AND created_at >= ?"
                params.append(since)
            if "created_at" in columns:
                query += " ORDER BY created_at DESC"
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            cursor = self.conn.execute(query, params)
            rows = [dict(row) for row in cursor.fetchall()]

        if format == "json":
            self._write_json(output_path, rows)
        elif format == "csv":
            self._write_csv(output_path, rows)
        else:
            raise ValueError(f"Unsupported format: {format}")

        return len(rows)

    def export_memory(
        self,
        output_path: str,
        format: str = "json",
        subject: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> int:
        """Export memory records to file.

        Args:
            output_path: Path to output file
            format: 'json' or 'csv'
            subject: Filter by subject
            limit: Maximum number of records

        Returns:
            Number of records exported
        """
        query = "SELECT * FROM personal_memory WHERE 1=1"
        params = []

        if subject:
            query += " AND owner = ?"
            params.append(subject)

        query += " ORDER BY created_at DESC"

        if limit:
            query += f" LIMIT {limit}"

        cursor = self.conn.execute(query, params)
        rows = [dict(row) for row in cursor.fetchall()]

        if format == "json":
            self._write_json(output_path, rows)
        elif format == "csv":
            self._write_csv(output_path, rows)
        else:
            raise ValueError(f"Unsupported format: {format}")

        return len(rows)

    def export_audit_log(
        self,
        output_path: str,
        format: str = "json",
        since: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> int:
        """Export audit log to file.

        Args:
            output_path: Path to output file
            format: 'json' or 'csv'
            since: ISO date string
            event_type: Filter by event type

        Returns:
            Number of records exported
        """
        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []

        if since:
            query += " AND timestamp >= ?"
            params.append(since)

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)

        query += " ORDER BY timestamp DESC"

        cursor = self.conn.execute(query, params)
        rows = [dict(row) for row in cursor.fetchall()]

        if format == "json":
            self._write_json(output_path, rows)
        elif format == "csv":
            self._write_csv(output_path, rows)
        else:
            raise ValueError(f"Unsupported format: {format}")

        return len(rows)

    def export_knowledge_graph(self, output_path: str, format: str = "json") -> int:
        """Export knowledge graph to file.

        Args:
            output_path: Path to output file
            format: 'json' or 'csv'

        Returns:
            Number of records exported
        """
        query = "SELECT * FROM knowledge_graph ORDER BY created_at DESC"
        cursor = self.conn.execute(query)
        rows = [dict(row) for row in cursor.fetchall()]

        if format == "json":
            self._write_json(output_path, rows)
        elif format == "csv":
            self._write_csv(output_path, rows)
        else:
            raise ValueError(f"Unsupported format: {format}")

        return len(rows)

    def export_all(
        self, output_dir: str, format: str = "json", since: Optional[str] = None
    ) -> Dict[str, int]:
        """Export all data to separate files.

        Args:
            output_dir: Directory for output files
            format: 'json' or 'csv'
            since: ISO date string for filtering

        Returns:
            Dict with counts per export type
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        counts = {}

        counts["tasks"] = self.export_tasks(
            f"{output_dir}/tasks_{timestamp}.{format}",
            format=format,
            since=since,
        )

        optional_exports = (
            ("memory", "personal_memory", self.export_memory, {}),
            ("audit", "audit_log", self.export_audit_log, {"since": since}),
            ("knowledge", "knowledge_graph", self.export_knowledge_graph, {}),
        )
        for name, table, export_fn, kwargs in optional_exports:
            path = f"{output_dir}/{name}_{timestamp}.{format}"
            if self._table_columns(table):
                counts[name] = export_fn(path, format=format, **kwargs)
            else:
                # A valid AIOS deployment may not enable every optional module.
                if format == "json":
                    self._write_json(path, [])
                else:
                    self._write_csv(path, [])
                counts[name] = 0

        return counts

    def _write_json(self, path: str, data: List[Dict]) -> None:
        """Write data as JSON."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "exported_at": datetime.now().isoformat(),
                    "count": len(data),
                    "data": data,
                },
                f,
                indent=2,
                default=str,
            )

    def _write_csv(self, path: str, data: List[Dict]) -> None:
        """Write data as CSV."""
        if not data:
            with open(path, "w") as f:
                f.write("")
            return

        keys = data[0].keys()
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(data)


class DataImporter:
    """Import data into AIOS database."""

    def __init__(self, db_path: str = "aios.sqlite") -> None:
        self.db_path = db_path
        self.conn = None

    def connect(self) -> None:
        """Connect to database."""
        self.conn = sqlite3.connect(self.db_path)

    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def __enter__(self) -> None:
        self.connect()
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def import_tasks(self, input_path: str, format: str = "json") -> int:
        """Import tasks from file.

        Args:
            input_path: Path to input file
            format: 'json' or 'csv'

        Returns:
            Number of records imported
        """
        if format == "json":
            data = self._read_json(input_path)
        elif format == "csv":
            data = self._read_csv(input_path)
        else:
            raise ValueError(f"Unsupported format: {format}")

        count = 0
        for record in data:
            try:
                self.conn.execute(
                    """INSERT OR IGNORE INTO tasks (id, status, created_at, updated_at)
                       VALUES (?, ?, ?, ?)""",
                    (
                        record.get("id"),
                        record.get("status", "pending"),
                        record.get("created_at"),
                        record.get("updated_at"),
                    ),
                )
                count += 1
            except Exception as e:
                print(f"Error importing record: {e}")

        self.conn.commit()
        return count

    def _read_json(self, path: str) -> List[Dict]:
        """Read a JSON file or the task export from an ``export_all`` directory."""
        source = Path(path)
        if source.is_dir():
            candidates = sorted(source.glob("tasks_*.json"), reverse=True)
            if not candidates:
                return []
            source = candidates[0]
        with open(source, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("data", data) if isinstance(data, dict) else data

    def _read_csv(self, path: str) -> List[Dict]:
        """Read CSV file."""
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)


# CLI entry point
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AIOS Data Export/Import")
    parser.add_argument("action", choices=["export", "import"], help="Action to perform")
    parser.add_argument("--db", default="aios.sqlite", help="Database path")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Export format")
    parser.add_argument("--output", "-o", default="./export", help="Output directory/file")
    parser.add_argument("--since", help="Export data since date (ISO format)")
    parser.add_argument("--limit", type=int, help="Maximum records to export")
    parser.add_argument(
        "--type",
        choices=["tasks", "memory", "audit", "knowledge", "all"],
        default="all",
    )

    args = parser.parse_args()

    if args.action == "export":
        with DataExporter(args.db) as exporter:
            if args.type == "all":
                counts = exporter.export_all(args.output, args.format, args.since)
                print(f"Exported: {counts}")
            elif args.type == "tasks":
                count = exporter.export_tasks(
                    args.output, args.format, args.limit, since=args.since
                )
                print(f"Exported {count} tasks")
            elif args.type == "memory":
                count = exporter.export_memory(args.output, args.format, args.limit)
                print(f"Exported {count} memory records")
            elif args.type == "audit":
                count = exporter.export_audit_log(args.output, args.format, since=args.since)
                print(f"Exported {count} audit records")
            elif args.type == "knowledge":
                count = exporter.export_knowledge_graph(args.output, args.format)
                print(f"Exported {count} knowledge graph entries")

    elif args.action == "import":
        with DataImporter(args.db) as importer:
            count = importer.import_tasks(args.output, args.format)
            print(f"Imported {count} records")
