"""Smoke-тесты сгенерированного модуля платформы prom."""


from aios_core.modules.prom import PromStorage
from aios_core.platforms import get_platform


def test_prom_storage_opens_and_counts():
    storage = PromStorage(":memory:")
    assert storage.get_ads() == []
    storage.close()


def test_prom_platform_registered():
    descriptor = get_platform("prom")
    assert descriptor.android_package == "ua.prom"


def test_prom_storage_subscriptions_empty():
    storage = PromStorage(":memory:")
    assert storage.subscriptions_list() == []
    storage.close()


def test_prom_storage_favorites_empty():
    storage = PromStorage(":memory:")
    assert storage.favorites_list() == []
    storage.close()
