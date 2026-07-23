"""OLX storage operations tests."""
from aios_core.modules.olx.storage import OLXStorage
def test_storage_operations():
    s = OLXStorage(":memory:")
    assert s.get_ads() == []
    assert s.stats() is not None
    s.close()
