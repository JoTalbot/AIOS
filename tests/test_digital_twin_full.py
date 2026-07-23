"""Digital twin full."""
from aios_core.digital_twin import DigitalTwin
def test(): s=DigitalTwin("dt1").stats(); assert isinstance(s,dict)
