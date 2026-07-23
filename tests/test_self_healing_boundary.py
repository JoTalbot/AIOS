"""self_healing boundary test."""
from aios_core.self_healing import SelfHealing

def test_stats_zero(): assert SelfHealing().stats() == {'strategies': 0}
