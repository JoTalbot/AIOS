"""model_serving standalone test."""
from aios_core.model_serving import ModelServer
def test_init(): s = ModelServer().stats(); assert isinstance(s, dict)
