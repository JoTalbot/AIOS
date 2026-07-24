"""Tests for Rozetka.ua platform scaffold."""

import json
import pytest

from aios_core.platforms import descriptor as descriptor_mod
from aios_core.platforms import get_platform, load_catalog_file


@pytest.fixture
def rozetka_registered():
    """Register rozetka platform from catalog."""
    loaded = load_catalog_file("platforms/rozetka.yaml")
    yield loaded
    for d in loaded:
        descriptor_mod._PLATFORMS.pop(d.name, None)


def test_catalog_rozetka_registered(rozetka_registered):
    """Rozetka platform loads from YAML catalog."""
    descriptor = get_platform("rozetka")
    assert descriptor.android_package == "com.rozetka"
    assert descriptor.extras["compliance"]["collector"] is True
    assert descriptor.extras["compliance"]["autopost_allowed"] is False
    assert descriptor.extras["compliance"]["messenger"] == "approval-only"
    storage = descriptor.storage_factory(":memory:")
    storage.close()


def test_rozetka_module_import_and_classes():
    """Rozetka module has Storage, Bootstrap, Messenger."""
    import importlib

    mod = importlib.import_module("aios_core.modules.rozetka")
    assert hasattr(mod, "RozetkaStorage")
    assert hasattr(mod, "RozetkaBootstrap")
    assert hasattr(mod, "RozetkaMessenger")


def test_rozetka_messenger_package_and_deep_link():
    """Rozetka messenger has correct PACKAGE and DEEP_LINK."""
    from aios_core.modules.rozetka import RozetkaMessenger

    assert RozetkaMessenger.PACKAGE == "com.rozetka"
    assert RozetkaMessenger.DEEP_LINK == "rozetka://chats"


def test_rozetka_bootstrap_package():
    """Rozetka bootstrap has correct PACKAGE."""
    from aios_core.modules.rozetka import RozetkaBootstrap

    assert RozetkaBootstrap.PACKAGE == "com.rozetka"


def test_rozetka_storage_inherits_olx():
    """Rozetka storage inherits OLXStorage schema."""
    from aios_core.modules.rozetka import RozetkaStorage
    from aios_core.modules.olx import AdCard

    with RozetkaStorage(":memory:") as storage:
        storage.save_ads([AdCard(title="iPhone 16", url="https://r.ua/1")])
        ads = storage.get_ads()
        assert len(ads) == 1
        assert ads[0].title == "iPhone 16"
