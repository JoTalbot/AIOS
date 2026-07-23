"""OLX storage full ops."""
from aios_core.modules.olx.storage import OLXStorage
def test(): s = OLXStorage(":memory:"); assert s.get_ads() == []; s.close()
