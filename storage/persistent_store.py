import sqlite3


class PersistentStore:
    """Minimal persistent storage layer for AIOS state."""

    def __init__(self, path="aios.db"):
        self.connection = sqlite3.connect(path)
        self._init()

    def _init(self):
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS memory (key TEXT PRIMARY KEY, value TEXT)"
        )
        self.connection.commit()

    def put(self, key, value):
        self.connection.execute(
            "INSERT OR REPLACE INTO memory VALUES (?, ?)",
            (key, value),
        )
        self.connection.commit()

    def get(self, key):
        row = self.connection.execute(
            "SELECT value FROM memory WHERE key=?", (key,)
        ).fetchone()
        return row[0] if row else None
