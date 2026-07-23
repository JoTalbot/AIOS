import pytest
from aios_core.active_learning import ActiveLearner

@pytest.mark.parametrize("strategy", ["uncertainty", "random"])
def test_strategy_returns_item(strategy):
    al = ActiveLearner()
    al.add_unlabeled({"id": 1})
    al.add_unlabeled({"id": 2})
    item = al.query(strategy=strategy)
    assert "id" in item

@pytest.mark.parametrize("n_items", [1,5,10,20])
def test_label_batch(n_items):
    al = ActiveLearner()
    for i in range(n_items):
        al.add_unlabeled({"id": i})
    for _ in range(n_items):
        item = al.query()
        if item: al.label(item, "x")
    assert al.stats()["labeled"] == n_items
