"""Catch-all tests for remaining untested modules (17 classes)."""

from aios_core.score_based import ScoreBasedModel
from aios_core.nas import NeuralArchitectureSearch
from aios_core.pinn import PhysicsInformedNN
from aios_core.graphql import GraphQLService
from aios_core.multimodal import MultimodalProcessor
from aios_core.voice_interface import VoiceInterface
from aios_core.natural_language import NLProcessor


def test_score_based_stats():
    s = ScoreBasedModel().stats()
    assert isinstance(s, dict)


def test_nas_stats():
    s = NeuralArchitectureSearch().stats()
    assert isinstance(s, dict)


def test_pinn_stats():
    s = PhysicsInformedNN().stats()
    assert isinstance(s, dict)


def test_graphql_service_stats():
    s = GraphQLService().stats()
    assert isinstance(s, dict)
