"""Model registry full ops."""
from aios_core.model_registry import ModelRegistry
def test_mr(): assert ModelRegistry().stats() is not None
