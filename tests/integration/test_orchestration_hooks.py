from core.runtime.orchestration_hooks import OrchestrationHooks


def test_hooks_emit():
    result = []
    hooks = OrchestrationHooks()
    hooks.register("start", lambda: result.append(True))
    hooks.emit("start")
    assert result == [True]
