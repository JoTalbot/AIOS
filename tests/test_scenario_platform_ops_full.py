"""Platform ops full scenario."""
from aios_core.platforms.catalog import PlatformCatalog
from aios_core.platforms.resolver import ProfileResolver
from aios_core.platforms.compliance import ComplianceGuard
from aios_core.platforms.secrets import SecretLoader
from aios_core.platforms.doctor import PlatformDoctor
def test_platform_ops():
    assert PlatformCatalog() is not None
    assert ProfileResolver() is not None
    assert ComplianceGuard() is not None
    assert PlatformDoctor() is not None
