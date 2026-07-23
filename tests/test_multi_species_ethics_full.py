"""Multi-species ethics full."""
from aios_core.universal_multi_species_ethics import UniversalMultiSpeciesEthics
def test(): s=UniversalMultiSpeciesEthics().stats(); assert isinstance(s,dict)
