"""Test safety honesty."""
from aios_core.ai_safety_honesty import HonestyFramework
def test_honesty(): assert HonestyFramework().stats() is not None
