"""Persistent storage abstraction."""

import sqlite3


class Database:
    def __init__(self, path='aios.db'):
        self.connection = sqlite3.connect(path)

    def set(self, key, value):
        self.connection.execute(
            'CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT)'
        )
        self.connection.execute(
            'INSERT OR REPLACE INTO state VALUES (?, ?)',
            (key, value)
        )
        self.connection.commit()

    def get(self, key):
        cursor = self.connection.execute(
            'SELECT value FROM state WHERE key=?', (key,)
        )
        row = cursor.fetchone()
        return row[0] if row else None
