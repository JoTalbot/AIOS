"""Smoke-тесты сгенерированного модуля платформы instagram."""

import pytest

from aios_core.platforms import get_platform, load_catalog_file
from aios_core.platforms import descriptor as descriptor_mod
from aios_core.modules.instagram import InstagramStorage


@pytest.fixture
def instagram_registered():
    """Регистрирует instagram из репозиторного YAML-каталога."""
    loaded = load_catalog_file("platforms/instagram.yaml")
    yield loaded[0]
    if loaded[0].name != "olx":  # не трогаем встроенные платформы
        descriptor_mod._PLATFORMS.pop(loaded[0].name, None)


def test_instagram_storage_opens_and_counts():
    storage = InstagramStorage(":memory:")
    assert storage.get_ads() == []
    storage.close()


def test_instagram_platform_registered(instagram_registered):
    descriptor = get_platform("instagram")
    assert descriptor.android_package == "com.instagram.android"
    assert descriptor.name == instagram_registered.name


def test_instagram_descriptor_factories_work(instagram_registered, tmp_path):
    storage = instagram_registered.make_storage(
        str(tmp_path / "instagram.sqlite")
    )
    assert storage.get_ads() == []
    storage.close()
    adb = instagram_registered.make_adb("emulator-5554")
    assert adb.package == "com.instagram.android"
    assert adb.serial == "emulator-5554"
