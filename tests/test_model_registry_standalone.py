"""model_registry standalone test."""
from aios_core.model_registry import ModelRegistry
def test_init(): s = ModelRegistry().stats(); assert isinstance(s, dict)
