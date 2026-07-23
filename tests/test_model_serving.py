"""Tests for Model Registry and Model Serving."""

from aios_core.model_registry import ModelRegistry
from aios_core.model_serving import ModelServer


def test_model_registry_stats():
    mr = ModelRegistry()
    s = mr.stats()
    assert isinstance(s, dict)


def test_model_server_stats():
    ms = ModelServer()
    s = ms.stats()
    assert isinstance(s, dict)
