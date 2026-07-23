"""active_learning boundary test."""
from aios_core.active_learning import ActiveLearner

def test_empty_query(): assert ActiveLearner().query() == {}
