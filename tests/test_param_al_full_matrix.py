"""Parametrized: active learning full."""
import pytest
from aios_core.active_learning import ActiveLearner

@pytest.mark.parametrize("n_unlabeled", [0,1,5,10,50,100])
def test_unlabeled_pool(n_unlabeled):
    al = ActiveLearner()
    for i in range(n_unlabeled): al.add_unlabeled({"id": i})
    assert al.stats()["unlabeled"] == n_unlabeled

@pytest.mark.parametrize("strategy", ["uncertainty","random"])
def test_strategies_with_data(strategy):
    al = ActiveLearner()
    al.add_unlabeled({"id": 1})
    al.add_unlabeled({"id": 2})
    assert "id" in al.query(strategy)
