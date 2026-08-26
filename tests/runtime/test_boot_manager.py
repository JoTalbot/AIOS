from core.runtime.boot_manager import BootManager


def test_boot_manager_exists():
    manager = BootManager()
    assert manager is not None
