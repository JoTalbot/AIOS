"""api_versioning smoke test."""
def test_api_v(): from aios_core.api_versioning import APIVersioning; assert APIVersioning() is not None
