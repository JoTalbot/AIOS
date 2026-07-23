"""Autonomy manager ops."""
from aios_core.autonomy_manager import AutonomyManager
def test_am(): s = AutonomyManager().stats(); assert isinstance(s, dict)
