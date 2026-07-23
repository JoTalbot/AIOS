"""Edge: active learning with empty pools."""
from aios_core.active_learning import ActiveLearner

def test_empty_query():
    assert ActiveLearner().query() == {}

def test_label_nonexistent():
    al = ActiveLearner()
    al.label({"id": 999}, "test")
    assert al.stats()["labeled"] == 1
    assert al.stats()["unlabeled"] == 0

def test_repeated_label():
    al = ActiveLearner()
    al.add_unlabeled({"id": 1})
    item = al.query()
    al.label(item, "x")
    al.label(item, "y")
    assert al.stats()["labeled"] == 1
