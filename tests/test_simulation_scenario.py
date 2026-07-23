from aios_core.simulation_engine import SimulationEngine
from aios_core.digital_twin import DigitalTwin
def test(): assert SimulationEngine().stats() is not None; assert DigitalTwin("t").stats() is not None
