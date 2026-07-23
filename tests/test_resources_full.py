"""Resources full ops."""
from aios_core.resources import ResourceManager
def test(): s=ResourceManager().stats(); assert isinstance(s,dict)
