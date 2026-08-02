from aios_core.v5.kernel.lifecycle import LifecycleManager, SystemState


def test_lifecycle_start():
    manager = LifecycleManager()
    manager.start()
    assert manager.state == SystemState.RUNNING
