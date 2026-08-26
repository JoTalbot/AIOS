from kernel.runtime_lifecycle import RuntimeLifecycle


class Manager:
    def __init__(self):
        self.recoveries = 0
        self.snapshots = 0

    def recover(self):
        self.recoveries += 1

    def snapshot(self):
        self.snapshots += 1


class Bootstrap:
    def __init__(self):
        self.initializations = 0
        self.shutdowns = 0

    def initialize(self):
        self.initializations += 1

    def shutdown(self):
        self.shutdowns += 1


class Context:
    def __init__(self):
        self.agent_manager = Manager()
        self.bootstrap = Bootstrap()


def test_lifecycle_repeated_calls_are_safe():
    context = Context()
    lifecycle = RuntimeLifecycle(context)

    lifecycle.start()
    lifecycle.start()
    lifecycle.stop()
    lifecycle.stop()

    assert context.agent_manager.recoveries == 2
    assert context.agent_manager.snapshots == 2
    assert context.bootstrap.initializations == 2
    assert context.bootstrap.shutdowns == 2
