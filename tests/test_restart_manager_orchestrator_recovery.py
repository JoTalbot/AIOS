from kernel.restart_manager import RestartManager


class Context:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.event_bus = None
        self.stopped = 0
        self.started = 0

    def stop(self):
        self.stopped += 1

    def start(self):
        self.started += 1


class Orchestrator:
    def __init__(self):
        self.calls = []

    async def stop(self):
        self.calls.append("stop")

    async def start(self):
        self.calls.append("start")


def test_restart_manager_restarts_vnext_orchestrator_and_runtime():
    orchestrator = Orchestrator()
    context = Context(orchestrator)
    RestartManager(context).restart()
    assert context.stopped == 1
    assert context.started == 1
    assert orchestrator.calls == ["stop", "start"]
