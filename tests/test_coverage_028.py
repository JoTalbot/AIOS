"""Test digital twin and simulation."""
from aios_core.digital_twin import DigitalTwin
from aios_core.simulation_engine import SimulationEngine
def test_dt(): assert DigitalTwin("test").stats() is not None
def test_se(): assert SimulationEngine().stats() is not None
