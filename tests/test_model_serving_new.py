"""model_serving test."""
def test(): from aios_core.model_serving import ModelServer; s = ModelServer().stats(); assert isinstance(s, dict)
