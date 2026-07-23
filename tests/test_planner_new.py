"""planner test."""
def test(): from aios_core.planner import Planner; s = Planner().stats(); assert isinstance(s, dict)
