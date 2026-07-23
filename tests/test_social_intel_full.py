"""Social intelligence full."""
from aios_core.social_intelligence import SocialIntelligence
def test(): s=SocialIntelligence().stats(); assert isinstance(s,dict)
