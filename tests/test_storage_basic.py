"""Basic tests for AIOS Database/Storage layer."""


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


class TestStorageAdvanced:
    """Advanced storage tests for better coverage."""

    def test_storage_with_config(self, tmp_path):
        """Test storage initialization with config."""
        from aios_core.config import AIOSConfig
        from aios_core.storage import Database

        # Create config
        config = AIOSConfig()
        config.database.path = str(tmp_path / "config_test.sqlite")

        # Initialize with config
        db = Database(None, config=config)
        assert db is not None

    def test_storage_schema_version(self, tmp_path):
        """Test schema version tracking."""
        from aios_core.storage import Database

        db_path = tmp_path / "schema_test.sqlite"
        db = Database(str(db_path))

        # Check schema version
        cursor = db.execute("SELECT version FROM schema_version")
        version = cursor.fetchone()

        # Should have schema version
        assert version is not None

    def test_storage_connection_access(self, tmp_path):
        """Test connection access."""
        from aios_core.storage import Database

        db_path = tmp_path / "context_test.sqlite"
        db = Database(str(db_path))

        # Access connection
        conn = db._conn
        conn.execute("SELECT 1")

    def test_storage_transaction_rollback(self, tmp_path):
        """Test transaction rollback on error."""
        from aios_core.storage import Database

        db_path = tmp_path / "rollback_test.sqlite"
        db = Database(str(db_path))

        # Create test table
        db.execute("CREATE TABLE test_rollback (id INTEGER PRIMARY KEY, value TEXT)")

        # Try to insert duplicate key (should fail)
        db.execute("INSERT INTO test_rollback VALUES (1, 'first')")

        try:
            db.execute("INSERT INTO test_rollback VALUES (1, 'duplicate')")
        except Exception:
            pass

        # First insert should still be there
        cursor = db.execute("SELECT COUNT(*) FROM test_rollback")
        count = cursor.fetchone()[0]
        assert count == 1
