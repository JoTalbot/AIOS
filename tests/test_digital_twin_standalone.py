"""digital_twin test."""
from aios_core.digital_twin import DigitalTwin
def test_init(): assert DigitalTwin("t").stats() is not None
