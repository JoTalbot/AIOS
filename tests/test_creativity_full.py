"""Creativity full ops."""
from aios_core.creativity import CreativeEngine
def test(): s=CreativeEngine().stats(); assert isinstance(s,dict)
