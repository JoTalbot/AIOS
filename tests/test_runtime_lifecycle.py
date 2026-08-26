from kernel.runtime_lifecycle import RuntimeLifecycle


class Manager:
    def __init__(self):
        self.calls = []

    def recover(self):
        self.calls.append("recover")

    def snapshot(self):
        self.calls.append("snapshot")


class Bootstrap:
    def __init__(self):
        self.calls = []

    def initialize(self):
        self.calls.append("initialize")

    def shutdown(self):
        self.calls.append("shutdown")


class Context:
    def __init__(self):
        self.agent_manager = Manager()
        self.bootstrap = Bootstrap()


def test_runtime_lifecycle_start_and_stop_are_ordered():
    context = Context()
    lifecycle = RuntimeLifecycle(context)

    assert lifecycle.start() is context
    assert context.agent_manager.calls == ["recover"]
    assert context.bootstrap.calls == ["initialize"]

    assert lifecycle.stop() is context
    assert context.agent_manager.calls == ["recover", "snapshot"]
    assert context.bootstrap.calls == ["initialize", "shutdown"]
