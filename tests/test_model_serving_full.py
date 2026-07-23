from aios_core.model_serving import ModelServer
def test(): assert ModelServer().stats() is not None