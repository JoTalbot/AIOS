"""Bigl storage ops."""
from aios_core.modules.bigl.storage import BiglStorage
def test(): s = BiglStorage(":memory:"); assert s is not None; s.close()
