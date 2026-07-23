"""simulation_engine test."""
from aios_core.simulation_engine import SimulationEngine
def test_init(): s = SimulationEngine().stats(); assert isinstance(s, dict)
