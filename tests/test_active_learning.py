"""Tests for Active Learning module."""

from aios_core.active_learning import ActiveLearner


def test_active_learner_add_and_query():
    learner = ActiveLearner()
    learner.add_unlabeled({"id": 1, "text": "hello"})
    learner.add_unlabeled({"id": 2, "text": "world"})

    item = learner.query(strategy="uncertainty")
    assert item["id"] == 1  # uncertainty returns first

    item = learner.query(strategy="random")
    assert "id" in item  # random returns any


def test_active_learner_label_moves_item():
    learner = ActiveLearner()
    learner.add_unlabeled({"id": 1})
    learner.add_unlabeled({"id": 2})

    item = learner.query()
    learner.label(item, "positive")

    assert learner.stats()["labeled"] == 1
    assert learner.stats()["unlabeled"] == 1


def test_active_learner_query_empty():
    learner = ActiveLearner()
    result = learner.query()
    assert result == {}


def test_active_learner_stats_initial():
    learner = ActiveLearner()
    s = learner.stats()
    assert s["labeled"] == 0
    assert s["unlabeled"] == 0
