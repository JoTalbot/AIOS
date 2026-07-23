from aios_core.model_registry import ModelRegistry
from aios_core.model_serving import ModelServer
def test(): assert ModelRegistry().stats() is not None; assert ModelServer().stats() is not None
