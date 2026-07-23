"""Storage DB ops."""
from aios_core.storage import Database
def test_memory(): db=Database(":memory:"); assert db.row_count("nonexistent") in (0,None); assert db.stats()["dialect"]=="sqlite"
