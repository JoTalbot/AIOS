"""Tools full ops."""
from aios_core.tools import ToolRegistry
def test(): s=ToolRegistry().stats(); assert isinstance(s,dict)
