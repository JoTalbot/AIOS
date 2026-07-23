"""OLX competitive analysis tests."""
from aios_core.modules.olx.competitive import CompetitorAnalyzer
from aios_core.modules.olx.competitive_watch import CompetitiveWatch
def test_competitive_tools_exist():
    assert CompetitorAnalyzer is not None
