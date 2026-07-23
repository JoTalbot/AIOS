"""digital_twin test."""
def test(): from aios_core.digital_twin import DigitalTwin; s = DigitalTwin("test").stats(); assert isinstance(s, dict)
