"""Active learning edge."""
from aios_core.active_learning import ActiveLearner
def test_empty(): assert ActiveLearner().query()=={}
def test_random(): al=ActiveLearner(); al.add_unlabeled({"id":1}); assert "id" in al.query("random")
