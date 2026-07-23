"""Model serving full ops."""
from aios_core.model_serving import ModelServer
def test_ms(): assert ModelServer().stats() is not None
