from aios_core.runtime.contracts import AgentStatus, AgentTask
from aios_core.runtime.sandbox import SandboxPolicy
from aios_core.runtime.sandbox_factory import build_default_sandbox_registry, build_sandbox_executor


def test_factory_binds_selected_backend_and_executes_handler():
    registry = build_default_sandbox_registry()
    executor = build_sandbox_executor(
        registry,
        "os",
        SandboxPolicy(allowed_permissions=("filesystem.read",)),
        command_handler=lambda task: __import__("aios_core.runtime.contracts", fromlist=["AgentResult"]).AgentResult(task.task_id, AgentStatus.COMPLETED, verdict="OK"),
    )
    result = executor.execute(AgentTask(id="sf1", goal="test", permissions=("filesystem.read",)))
    assert result.status is AgentStatus.COMPLETED
    assert result.verdict == "OK"


def test_factory_fails_on_unknown_backend():
    registry = build_default_sandbox_registry()
    try:
        build_sandbox_executor(registry, "missing", SandboxPolicy())
    except KeyError:
        pass
    else:
        raise AssertionError("unknown backend must fail closed")
