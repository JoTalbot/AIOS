"""Tests for knowledge, graph, and domain-specific modules."""

from aios_core.knowledge_distillation import KnowledgeDistillation
from aios_core.graph_transformer import GraphTransformer
from aios_core.self_supervised import SelfSupervisedLearner
from aios_core.transfer_learning import TransferLearner
from aios_core.meta_learning import MetaLearner


def test_knowledge_distillation_stats():
    s = KnowledgeDistillation().stats()
    assert isinstance(s, dict)


def test_graph_transformer_stats():
    s = GraphTransformer().stats()
    assert isinstance(s, dict)


def test_self_supervised_stats():
    s = SelfSupervisedLearner().stats()
    assert isinstance(s, dict)


def test_transfer_learner_stats():
    s = TransferLearner().stats()
    assert isinstance(s, dict)


def test_meta_learner_stats():
    s = MetaLearner().stats()
    assert isinstance(s, dict)
