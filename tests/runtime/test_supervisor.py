from core.runtime.supervisor import RuntimeSupervisor
from core.supervision.supervisor import Supervisor


class DummyPersistence:
    def __init__(self):
        self.records = []

    def record(self, item):
        self.records.append(item)


class DummyRecovery:
    def evaluate(self, signal):
        return {"action": "retry", "component": signal.component}


def test_supervisor_lifecycle():
    supervisor = RuntimeSupervisor()
    supervisor.start()
    assert supervisor.running
    supervisor.stop()
    assert not supervisor.running


def test_supervisor_records_recovery_decision():
    persistence = DummyPersistence()
    supervisor = Supervisor(
        recovery=DummyRecovery(),
        persistence=persistence,
    )

    decision = supervisor.observe("worker", "failure", "boom")

    assert decision["action"] == "retry"
    assert len(persistence.records) == 1
    assert persistence.records[0]["type"] == "recovery_decision"
