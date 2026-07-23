"""Mamba full ops."""
from aios_core.mamba import MambaModel
def test(): s=MambaModel().stats(); assert isinstance(s,dict)
