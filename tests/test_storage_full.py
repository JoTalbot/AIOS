"""Storage full tests."""
from aios_core.storage import Database
def test_db_memory():
    db = Database(":memory:")
    assert db.tables() == []
    assert db.stats()["dialect"] == "sqlite"
