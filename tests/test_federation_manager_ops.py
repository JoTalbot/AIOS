"""Federation manager ops."""
from aios_core.federation_manager import FederationManager
def test_fm(): s = FederationManager().stats(); assert isinstance(s, dict)
