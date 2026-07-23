"""Parametrized model type tests."""
import pytest
from aios_core.model_registry import ModelRegistry
from aios_core.model_serving import ModelServer

@pytest.mark.parametrize("model_name", [
    "model_v1", "classifier_x", "regressor_y", "ensemble_z",
])
def test_registry_stats(model_name):
    mr = ModelRegistry()
    ms = ModelServer()
    assert mr.stats() is not None
    assert ms.stats() is not None
