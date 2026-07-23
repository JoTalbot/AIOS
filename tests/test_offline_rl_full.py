"""Offline RL full."""
from aios_core.offline_rl import OfflineRL
def test(): s=OfflineRL().stats(); assert isinstance(s,dict)
