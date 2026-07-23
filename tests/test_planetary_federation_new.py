"""planetary_federation test."""
def test(): from aios_core.planetary_federation import PlanetaryFederation; s = PlanetaryFederation().stats(); assert isinstance(s, dict)
