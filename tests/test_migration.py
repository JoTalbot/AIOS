"""Tests for database migration system."""

from aios_core.migration import Migration, MigrationManager


def test_migration_creation():
    m = Migration(version="1.0.0", description="init", up_sql="CREATE TABLE test (id INT)")
    assert m.version == "1.0.0"
    assert m.description == "init"


def test_migration_manager_init():
    mm = MigrationManager(":memory:")
    assert mm is not None


def test_migration_manager_add():
    mm = MigrationManager(":memory:")
    m = Migration(version="1.0.0", description="init", up_sql="CREATE TABLE test (id INT)")
    mm.add_migration(m)
    assert len(mm.migrations) == 1
