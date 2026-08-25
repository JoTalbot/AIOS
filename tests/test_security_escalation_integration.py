from aios_core.openhands.policy_resolver import resolve_ci_policy
from aios_core.openhands.specialist_spawner import SpecialistSpawner


class FakeClient:
    def __init__(self):
        self.started = []

    def start_conversation(self, prompt, **kwargs):
        self.started.append((prompt, kwargs))
        return {"conversation_id": "security-conv-1"}

    def wait_start_task(self, start_task_id, **kwargs):
        raise AssertionError("no start task expected")

    def wait_execution(self, conversation_id, **kwargs):
        return "completed"


def test_security_policy_escalates_to_specialist():
    changed = ["auth/service.py"]
    policy = resolve_ci_policy("Update authentication flow", changed)

    assert policy.security_forced is True

    client = FakeClient()
    spawned = SpecialistSpawner(client, repository="JoTalbot/AIOS").spawn(
        role="security",
        task_id="T-SEC-1",
        title="Authentication update",
        description="Update authentication flow",
        changed_files=changed,
        branch="agent/oh-T-SEC-1",
        reasons=policy.reasons,
    )

    assert spawned.conversation_id == "security-conv-1"
    assert len(client.started) == 1
    prompt, kwargs = client.started[0]
    assert "auth/service.py" in prompt
    assert "APPROVED" in prompt
    assert kwargs["branch"] == "agent/oh-T-SEC-1"
