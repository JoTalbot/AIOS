"""Tests for Platform infrastructure — catalog, resolver, secrets."""

from aios_core.platforms import list_platforms
from aios_core.platforms.catalog import load_catalog
from aios_core.platforms.secrets import env_name


def test_list_platforms():
    plats = list_platforms()
    assert isinstance(plats, list)
    # Core platforms should be registered
    names = [p.name for p in plats]
    assert "olx" in names


def test_load_catalog_returns_platforms():
    plats = load_catalog()
    assert isinstance(plats, list)
    assert len(plats) > 0


def test_env_name_format():
    name = env_name("instagram", "LOGIN")
    assert name == "AIOS_SECRET__INSTAGRAM__LOGIN"


def test_env_name_with_profile():
    name = env_name("olx", "PASSWORD", profile="work")
    assert name == "AIOS_SECRET__OLX__WORK__PASSWORD"
