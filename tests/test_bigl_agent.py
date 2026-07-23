"""Smoke-тесты сгенерированного модуля платформы bigl."""

import pytest

from aios_core.modules.bigl import BiglStorage
from aios_core.platforms import get_platform


def test_bigl_storage_opens_and_counts():
    storage = BiglStorage(":memory:")
    assert storage.get_ads() == []
    storage.close()


def test_bigl_platform_registered():
    descriptor = get_platform("bigl")
    assert descriptor.android_package == "ua.bigl"


def test_bigl_storage_subscriptions_empty():
    storage = BiglStorage(":memory:")
    assert storage.subscriptions_list() == []
    storage.close()


def test_bigl_storage_favorites_empty():
    storage = BiglStorage(":memory:")
    assert storage.favorites_list() == []
    storage.close()
