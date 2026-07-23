"""Viber storage ops."""
from aios_core.modules.viber.storage import ViberStorage
def test(): s = ViberStorage(":memory:"); assert s is not None; s.close()
