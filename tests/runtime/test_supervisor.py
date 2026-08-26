from core.runtime.supervisor import RuntimeSupervisor


def test_supervisor_lifecycle():
    supervisor = RuntimeSupervisor()
    supervisor.start()
    assert supervisor.running
    supervisor.stop()
    assert not supervisor.running
