from aios_core.production_autopilot import ProductionAutopilot
def test(): s = ProductionAutopilot().stats(); assert isinstance(s, dict)
