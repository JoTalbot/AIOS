"""Tests for advanced ML/NN modules — Bayesian, continual, curriculum, transformers."""

from aios_core.bayesian import BayesianInference
from aios_core.continual_learning import ContinualLearner
from aios_core.curriculum_learning import CurriculumLearner
from aios_core.hierarchical_rl import HierarchicalRL


def test_bayesian_inference_stats():
    s = BayesianInference().stats()
    assert isinstance(s, dict)


def test_continual_learner_stats():
    s = ContinualLearner().stats()
    assert isinstance(s, dict)


def test_curriculum_learner_stats():
    s = CurriculumLearner().stats()
    assert isinstance(s, dict)


def test_hierarchical_rl_stats():
    s = HierarchicalRL().stats()
    assert isinstance(s, dict)
