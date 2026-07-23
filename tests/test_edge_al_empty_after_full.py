"""Edge: active learning empty after full."""
from aios_core.active_learning import ActiveLearner
def test_empty_after_label_all():
    al = ActiveLearner()
    for i in range(10): al.add_unlabeled({"id": i})
    for _ in range(10):
        item = al.query()
        if item: al.label(item, "x")
    assert al.stats()["unlabeled"] == 0
    assert al.stats()["labeled"] == 10
    assert al.query() == {}
