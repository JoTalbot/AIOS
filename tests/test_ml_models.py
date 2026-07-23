"""Tests for ML model management, serving, and NLP."""

from aios_core.model_registry import ModelRegistry
from aios_core.model_serving import ModelServer
from aios_core.model_based_rl import ModelBasedRL


def test_model_registry_init():
    mr = ModelRegistry()
    assert mr is not None


def test_model_server_init():
    ms = ModelServer()
    assert ms is not None


def test_model_based_rl_init():
    mrl = ModelBasedRL()
    assert mrl is not None
