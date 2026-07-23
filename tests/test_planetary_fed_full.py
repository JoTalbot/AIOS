"""Planetary federation full."""
from aios_core.planetary_federation import PlanetaryFederation
def test(): s=PlanetaryFederation().stats(); assert isinstance(s,dict)
