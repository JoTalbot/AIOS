"""model_registry test."""
def test(): from aios_core.model_registry import ModelRegistry; s = ModelRegistry().stats(); assert isinstance(s, dict)
