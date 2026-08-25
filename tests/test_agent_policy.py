from aios_core.runtime.contracts import AgentTask
from aios_core.runtime.policy import PolicyDecision, PolicyEngine


def test_policy_denies_unlisted_permission():
    result = PolicyEngine().check(AgentTask(id="t1", goal="x"), "shell.execute")
    assert result.decision is PolicyDecision.DENY


def test_policy_allows_explicit_permission():
    task = AgentTask(id="t2", goal="x", permissions=("filesystem.read",))
    result = PolicyEngine().check(task, "filesystem.read")
    assert result.decision is PolicyDecision.ALLOW


def test_policy_requires_approval_for_sensitive_permission():
    task = AgentTask(id="t3", goal="x", permissions=("production.deploy",))
    result = PolicyEngine(approval_permissions=("production.deploy",)).check(task, "production.deploy")
    assert result.decision is PolicyDecision.APPROVAL_REQUIRED


def test_policy_sandboxes_risky_permission():
    task = AgentTask(id="t4", goal="x", permissions=("shell.execute",))
    result = PolicyEngine(sandbox_permissions=("shell.execute",)).check(task, "shell.execute")
    assert result.decision is PolicyDecision.SANDBOX
