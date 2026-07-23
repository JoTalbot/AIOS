"""Parametrized: all storage tables."""
import pytest
from aios_core.storage import Database

@pytest.mark.parametrize("table", [
    "audit_events","approvals","memory_items","kg_nodes","kg_edges",
    "evolution_records","events","plans","capabilities","tasks",
])
def test_every_table(table):
    db = Database(":memory:")
    c = db.row_count(table)
    assert c in (0, None)

@pytest.mark.parametrize("count", [1,3,5])
def test_tables_list(count):
    db = Database(":memory:")
    tables = db.tables()
    assert isinstance(tables, list)
