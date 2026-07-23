"""resources standalone test."""
from aios_core.resources import ResourceManager
def test_init(): s = ResourceManager().stats(); assert isinstance(s, dict)
