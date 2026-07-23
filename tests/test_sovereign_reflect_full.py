"""Sovereign reflection full."""
from aios_core.sovereign_reflection import SovereignReflection
def test(): s=SovereignReflection().stats(); assert isinstance(s,dict)
