"""Tests for aios_core/self_supervised.py"""
from __future__ import annotations
import pytest
from aios_core.self_supervised import SelfSupervisedLearner


@pytest.fixture()
def learner():
    return SelfSupervisedLearner()


class TestSelfSupervisedLearner:
    def test_create(self, learner):
        assert learner is not None

    def test_generate_pseudo_label(self, learner):
        result = learner.generate_pseudo_label(data=[1.0, 2.0, 3.0])
        assert result is not None

    def test_generate_batch_pseudo_labels(self, learner):
        data_list = [[1.0, 2.0], [3.0, 4.0]]
        result = learner.generate_batch_pseudo_labels(data_list)
        assert isinstance(result, list)

    def test_add_augmentation(self, learner):
        learner.add_augmentation(name="noise", intensity=0.1, probability=0.5)

    def test_augment(self, learner):
        learner.add_augmentation(name="noise")
        result = learner.augment(data=[1.0, 2.0, 3.0])
        assert isinstance(result, (list, dict))

    def test_create_augmented_pair(self, learner):
        result = learner.create_augmented_pair(data=[1.0, 2.0, 3.0])
        assert isinstance(result, (list, tuple, dict))

    def test_contrastive_loss(self, learner):
        embeddings = [[1.0, 0.0], [0.0, 1.0], [1.0, 0.0]]
        result = learner.contrastive_loss(embeddings)
        assert isinstance(result, (int, float))

    def test_stats(self, learner):
        s = learner.stats()
        assert isinstance(s, dict)
