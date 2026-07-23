"""models standalone test."""
from aios_core.models import ModelManager
def test_init(): s = ModelManager().stats(); assert isinstance(s, dict)
