"""federation_manager test."""
def test(): from aios_core.federation_manager import FederationManager; s = FederationManager().stats(); assert isinstance(s, dict)
