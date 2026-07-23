"""Production AP ops."""
from aios_core.production_autopilot import ProductionAutopilot
def test_stats(): assert ProductionAutopilot().stats() is not None
