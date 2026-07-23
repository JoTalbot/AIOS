"""Smoke-тесты сгенерированного модуля платформы shafa."""

import pytest

from aios_core.modules.shafa import ShafaStorage
from aios_core.platforms import get_platform


def test_shafa_storage_opens_and_counts():
    storage = ShafaStorage(":memory:")
    assert storage.get_ads() == []
    storage.close()


def test_shafa_platform_registered():
    descriptor = get_platform("shafa")
    assert descriptor.android_package == "com.shafa"


def test_shafa_storage_subscriptions_empty():
    storage = ShafaStorage(":memory:")
    assert storage.subscriptions_list() == []
    storage.close()


def test_shafa_storage_favorites_empty():
    storage = ShafaStorage(":memory:")
    assert storage.favorites_list() == []
    storage.close()
