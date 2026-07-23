"""tools standalone test."""
from aios_core.tools import ToolRegistry
def test_init(): s = ToolRegistry().stats(); assert isinstance(s, dict)
