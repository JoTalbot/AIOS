from aios_core.openhands.specialist_spawner import SpecialistSpawner


class FakeClient:
    def __init__(self, result=None):
        self.result = result or {"conversation_id": "conv-security-1", "start_task_id": "task-1"}
        self.calls = []

    def start_conversation(self, prompt, **kwargs):
        self.calls.append(("start", prompt, kwargs))
        return self.result

    def wait_start_task(self, start_task_id, **kwargs):
        self.calls.append(("start_wait", start_task_id))
        return {"status": "started"}

    def wait_execution(self, conversation_id, **kwargs):
        self.calls.append(("execution_wait", conversation_id))
        return "completed"


def test_spawner_starts_and_waits_for_specialist():
    client = FakeClient()
    result = SpecialistSpawner(client, repository="JoTalbot/AIOS").spawn(
        role="security", task_id="T-1", title="Security review",
        description="Review authentication changes", changed_files=["auth/service.py"],
        branch="agent/oh-T-1", reasons=("auth path",),
    )
    assert result.conversation_id == "conv-security-1"
    assert result.start_task_id == "task-1"
    assert [call[0] for call in client.calls] == ["start", "start_wait", "execution_wait"]
    assert "auth/service.py" in client.calls[0][1]
    assert "APPROVED" in client.calls[0][1]


def test_spawner_fails_closed_without_conversation_id():
    client = FakeClient(result={"start_task_id": "task-1"})
    try:
        SpecialistSpawner(client).spawn(
            role="security", task_id="T-2", title="Security review",
            description="Review changes", changed_files=[".github/workflows/ci.yml"],
            branch="agent/oh-T-2",
        )
    except RuntimeError as exc:
        assert "conversation_id" in str(exc)
    else:
        raise AssertionError("spawner must fail closed when OpenHands returns no conversation id")
