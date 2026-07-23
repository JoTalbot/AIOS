"""AIOS Database Migration System"""

import os
import sqlite3
from typing import List


class Migration:
    """Represents a single database migration."""

    def __init__(self, version: str, description: str, up_sql: str, down_sql: str = ""):
        self.version = version
        self.description = description
        self.up_sql = up_sql
        self.down_sql = down_sql


class MigrationManager:
    """Manages database schema migrations."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.migrations: List[Migration] = []

    def add_migration(self, migration: Migration):
        self.migrations.append(migration)

    def create_migrations_table(self, conn: sqlite3.Connection):
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    def get_applied_versions(self, conn: sqlite3.Connection) -> set:
        try:
            rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
            return {row[0] for row in rows}
        except:
            return set()

    def migrate(self):
        conn = sqlite3.connect(self.db_path)
        self.create_migrations_table(conn)
        applied = self.get_applied_versions(conn)

        for migration in sorted(self.migrations, key=lambda m: m.version):
            if migration.version not in applied:
                print(
                    f"Applying migration {migration.version}: {migration.description}"
                )
                conn.executescript(migration.up_sql)
                conn.execute(
                    "INSERT INTO schema_migrations (version) VALUES (?)",
                    (migration.version,),
                )
                conn.commit()

        conn.close()
        print("Migrations completed.")
