from core.runtime.lifecycle_controller import LifecycleController


def test_lifecycle_controller_cycle():
    controller = LifecycleController()
    assert controller.start().status == "running"
    assert controller.stop().status == "stopped"
