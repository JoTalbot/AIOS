"""Parametrized deep: active_learning."""
import pytest
from aios_core.active_learning import ActiveLearner
@pytest.mark.parametrize("strategy",["uncertainty","random"])
def test_al(strategy):
    al = ActiveLearner()
    al.add_unlabeled({"id":1})
    assert "id" in al.query(strategy)

