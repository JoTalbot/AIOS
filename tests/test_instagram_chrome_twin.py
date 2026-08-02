"""Tests for Instagram Chrome Twin adapter (без запуска браузера)."""
import pytest


def test_registry_has_instagram_chrome_twin():
    """Адаптер зарегистрирован в реестре платформ."""
    from aios_core.platforms.registry import PlatformRegistry
    r = PlatformRegistry()
    assert "instagram_chrome_twin" in r._adapter_classes


def test_adapter_importable():
    """Класс импортируется."""
    from aios_core.platforms.instagram_chrome_twin_adapter import InstagramChromeTwinAdapter
    assert InstagramChromeTwinAdapter is not None


def test_yaml_exists():
    """Конфиг-файл платформы на месте."""
    from pathlib import Path
    assert Path("platforms/instagram_chrome_twin.yaml").exists()
