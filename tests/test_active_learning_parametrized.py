"""Parametrized tests for Active Learning."""

import pytest
from aios_core.active_learning import ActiveLearner


@pytest.mark.parametrize("strategy", ["uncertainty", "random"])
def test_query_returns_item(strategy):
    learner = ActiveLearner()
    learner.add_unlabeled({"id": 1})
    result = learner.query(strategy=strategy)
    assert isinstance(result, dict)
    assert "id" in result


@pytest.mark.parametrize("label", ["positive", "negative", "neutral", "spam"])
def test_label_moves_to_labeled(label):
    learner = ActiveLearner()
    learner.add_unlabeled({"id": 1})
    item = learner.query()
    learner.label(item, label)
    assert learner.stats()["labeled"] == 1
    assert learner.stats()["unlabeled"] == 0
