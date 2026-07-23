"""Full learning pipeline scenario."""
from aios_core.active_learning import ActiveLearner
from aios_core.benchmark import Benchmark
from aios_core.knowledge_graph import KnowledgeGraph

def test_learning_to_kg():
    al = ActiveLearner()
    kg = KnowledgeGraph()
    for i in range(10):
        al.add_unlabeled({"id": i, "text": f"sample_{i}"})
    assert al.stats()["unlabeled"] == 10
    for _ in range(10):
        item = al.query()
        if item: al.label(item, "positive")
    assert al.stats()["labeled"] == 10
    kg.add_node("learned_data", {"count": al.stats()["labeled"]})
    assert kg.stats() is not None
