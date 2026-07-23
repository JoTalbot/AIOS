from aios_core.marketplace import Marketplace
def test(): s = Marketplace().stats(); assert isinstance(s, dict)
