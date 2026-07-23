from aios_core.federation_manager import FederationManager
def test(): s = FederationManager().stats(); assert isinstance(s, dict)
