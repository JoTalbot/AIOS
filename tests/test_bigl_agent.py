"""Smoke-тесты сгенерированного модуля платформы bigl."""

from aios_core.platforms import get_platform
from aios_core.modules.bigl import BiglStorage


def test_bigl_storage_opens_and_counts():
    storage = BiglStorage(":memory:")
    assert storage.get_ads() == []
    storage.close()


def test_bigl_platform_registered():
    descriptor = get_platform("bigl")
    assert descriptor.android_package == "ua.bigl"
