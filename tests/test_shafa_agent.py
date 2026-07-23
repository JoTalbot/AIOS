"""Smoke-тесты сгенерированного модуля платформы shafa."""

from aios_core.modules.shafa import ShafaStorage
from aios_core.platforms import get_platform


def test_shafa_storage_opens_and_counts():
    storage = ShafaStorage(":memory:")
    assert storage.get_ads() == []
    storage.close()


def test_shafa_platform_registered():
    descriptor = get_platform("shafa")
    assert descriptor.android_package == "com.shafa"
