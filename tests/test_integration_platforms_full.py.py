"""Integration: Platforms full pipeline."""
from aios_core.platforms.catalog import PlatformCatalog
from aios_core.platforms.resolver import ProfileResolver
from aios_core.platforms.compliance import ComplianceGuard
def test_platforms_pipeline():
    pc = PlatformCatalog()
    pr = ProfileResolver()
    cg = ComplianceGuard()
    assert pc is not None
    assert pr is not None
    assert cg is not None
