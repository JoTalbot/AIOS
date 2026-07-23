import pytest
from aios_core.storage import Database

@pytest.mark.parametrize("table", ["audit_events", "approvals", "tasks", "plans"])
def test_table_exists_or_zero(table):
    db = Database(":memory:")
    c = db.row_count(table)
    assert c in (0, None)

@pytest.mark.parametrize("method", ["new_id", "now_iso"])
def test_static_methods(method):
    result = getattr(Database, method)()
    assert isinstance(result, str)
    assert len(result) > 0
