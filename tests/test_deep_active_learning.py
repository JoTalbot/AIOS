"""Deep active learning pipeline."""
from aios_core.active_learning import ActiveLearner
def test_uncertainty_vs_random():
    al = ActiveLearner()
    for i in range(5): al.add_unlabeled({"id": i})
    u = al.query("uncertainty")
    r = al.query("random")
    assert "id" in u and "id" in r
def test_relabel_protection():
    al = ActiveLearner()
    al.add_unlabeled({"id": 1})
    item = al.query()
    al.label(item, "x")
    al.label(item, "y")
    assert al.stats()["labeled"] == 1
