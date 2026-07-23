"""Basic tests for AIOS Database/Storage layer."""

import pytest
import sqlite3
from aios_core.storage import Database


class TestDatabase:
    """Basic database tests."""
    
    def test_database_creation(self, tmp_path):
        """Test database can be created."""
        db_path = tmp_path / "test.sqlite"
        db = Database(str(db_path))
        assert db is not None
    
    def test_database_connection(self, tmp_path):
        """Test database connection works."""
        db_path = tmp_path / "test.sqlite"
        db = Database(str(db_path))
        
        # Should be able to execute queries
        result = db.execute("SELECT 1")
        assert result is not None
    
    def test_database_tables_created(self, tmp_path):
        """Test database tables are created on initialization."""
        db_path = tmp_path / "test.sqlite"
        db = Database(str(db_path))
        
        # Check tables exist
        cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        assert len(tables) > 0
    
    def test_database_insert_and_query(self, tmp_path):
        """Test basic insert and query operations."""
        db_path = tmp_path / "test.sqlite"
        db = Database(str(db_path))
        
        # Create test table
        db.execute("CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, value TEXT)")
        
        # Insert
        db.execute("INSERT INTO test_table (value) VALUES (?)", ("test_value",))
        
        # Query
        cursor = db.execute("SELECT value FROM test_table")
        result = cursor.fetchone()
        
        assert result is not None
        assert result[0] == "test_value"
