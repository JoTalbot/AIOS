from core.runtime.supervisor import RuntimeSupervisor
from core.supervision.supervisor import Supervisor


class DummyPersistence:
    def __init__(self):
        self.records = []

    def record(self, item):
        self.records.append(item)


class SemanticPersistence:
    def __init__(self):
        self.records = []

    def record_recovery(self, item):
        self.records.append(item)


class DummyRecovery:
    def evaluate(self, signal):
        return {"action": "retry", "component": signal.component}


def test_supervisor_lifecycle():
    supervisor = RuntimeSupervisor()
    supervisor.running = True
    assert supervisor.running
    supervisor.running = False
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


def test_supervisor_prefers_semantic_recovery_persistence():
    persistence = SemanticPersistence()
    supervisor = Supervisor(
        recovery=DummyRecovery(),
        persistence=persistence,
    )

    decision = supervisor.observe("worker", "failure", "boom")

    assert decision["action"] == "retry"
    assert persistence.records == [
        {
            "type": "recovery_decision",
            "component": "worker",
            "decision": decision,
        }
    ]
