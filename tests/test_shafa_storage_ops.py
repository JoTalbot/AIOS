"""Shafa storage ops."""
from aios_core.modules.shafa.storage import ShafaStorage
def test(): s = ShafaStorage(":memory:"); assert s is not None; s.close()
