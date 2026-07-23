"""test_active_learning_scenario test."""
from aios_core.active_learning import ActiveLearner

def test_full_cycle():
    al = ActiveLearner()
    for i in range(20): al.add_unlabeled({"id": i})
    assert al.stats()["unlabeled"] == 20
    for _ in range(10):
        item = al.query()
        if not item: break
        al.label(item, "class_x")
    assert al.stats()["labeled"] == 10
    assert al.stats()["unlabeled"] == 10
