"""Simulation engine full."""
from aios_core.simulation_engine import SimulationEngine
def test(): s=SimulationEngine().stats(); assert isinstance(s,dict)
