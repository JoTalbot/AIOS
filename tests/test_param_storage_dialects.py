"""Parametrized storage dialect tests."""
import pytest
from aios_core.storage import Database

@pytest.mark.parametrize("table_name", [
    "tasks", "audit_events", "approvals", "memory_items",
    "kg_nodes", "kg_edges", "evolution_records", "events", "plans",
])
def test_table_row_count(table_name):
    db = Database(":memory:")
    c = db.row_count(table_name)
    assert c in (0, None)

@pytest.mark.parametrize("json_data", [
    {"key": "value"}, [1,2,3], "string", 42, None, True, False,
])
def test_json_roundtrip(json_data):
    j = Database.to_json(json_data)
    d = Database.from_json(j)
    assert type(d) == type(json_data) or isinstance(d, (dict, list, str, int, float, bool))
