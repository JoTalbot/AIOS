"""social_intelligence test."""
def test(): from aios_core.social_intelligence import SocialIntelligence; s = SocialIntelligence().stats(); assert isinstance(s, dict)
