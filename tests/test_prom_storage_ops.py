"""Prom storage ops."""
from aios_core.modules.prom.storage import PromStorage
def test(): s = PromStorage(":memory:"); assert s is not None; s.close()
