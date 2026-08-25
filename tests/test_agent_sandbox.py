from aios_core.runtime.contracts import AgentResult, AgentStatus, AgentTask
from aios_core.runtime.sandbox import SandboxExecutor, SandboxPolicy


def test_sandbox_blocks_unapproved_permission():
    calls = []
    sandbox = SandboxExecutor(
        lambda task: calls.append(task.task_id) or AgentResult(task.task_id, AgentStatus.COMPLETED),
        SandboxPolicy(allowed_permissions=("filesystem.read",)),
    )
    result = sandbox.execute(AgentTask(id="s1", goal="x", permissions=("shell.execute",)))
    assert result.status is AgentStatus.BLOCKED
    assert calls == []


def test_sandbox_blocks_network_by_default():
    sandbox = SandboxExecutor(lambda task: AgentResult(task.task_id, AgentStatus.COMPLETED), SandboxPolicy(allowed_permissions=("network",)))
    result = sandbox.execute(AgentTask(id="s2", goal="x", permissions=("network",)))
    assert result.status is AgentStatus.BLOCKED


def test_sandbox_allows_policy_compliant_task():
    sandbox = SandboxExecutor(lambda task: AgentResult(task.task_id, AgentStatus.COMPLETED, verdict="SANDBOX_OK"), SandboxPolicy(allowed_permissions=("filesystem.read",), filesystem=False))
    result = sandbox.execute(AgentTask(id="s3", goal="x", permissions=("filesystem.read",)))
    assert result.status is AgentStatus.COMPLETED
    assert result.verdict == "SANDBOX_OK"
