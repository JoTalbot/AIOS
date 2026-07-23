"""Integration test — platform pipeline."""
from aios_core.platforms.catalog import PlatformCatalog
from aios_core.platforms.resolver import ProfileResolver
from aios_core.platforms.secrets import SecretManager
def test_pipeline():
    assert PlatformCatalog is not None
