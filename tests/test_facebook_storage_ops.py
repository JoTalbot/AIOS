"""Facebook storage ops."""
from aios_core.modules.facebook.storage import FacebookStorage
def test(): s = FacebookStorage(":memory:"); assert s is not None; s.close()
