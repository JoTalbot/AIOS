"""simulation_engine test."""
def test(): from aios_core.simulation_engine import SimulationEngine; s = SimulationEngine().stats(); assert isinstance(s, dict)
