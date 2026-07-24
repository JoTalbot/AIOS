"""AIOS test configuration."""

import pytest

# Enable pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


def pytest_configure(config):
    """Set asyncio mode to auto for async test support + markers."""
    if hasattr(config.option, "asyncio_mode"):
        config.option.asyncio_mode = "auto"
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-k \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "real_device: marks tests requiring a real Android device")


@pytest.fixture(autouse=True, scope="function")
def _isolate_platform_registry():
    """Изолировать глобальный реестр платформ (_PLATFORMS) для каждого теста.

    Snapshot/restore: перед тестом сохраняем ключи _PLATFORMS,
    после теста удаляем все ключи, которых не было в snapshot.
    Это предотвращает race conditions при параллельном запуске (xdist).
    """
    from aios_core.platforms.descriptor import restore_registry, snapshot_registry

    snapshot = snapshot_registry()
    yield
    restore_registry(snapshot)
