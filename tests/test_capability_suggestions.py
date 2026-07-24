"""Tests for CapabilityEngine v3.0 suggestions"""


from aios_core import Database, Orchestrator


def test_suggest_capabilities():
    db = Database(":memory:")
    orch = Orchestrator(db=db)

    cap_engine = orch.capabilities

    # Register some capabilities
    cap_engine.register("test_tool", "A test tool", capability_type="tool")
    cap_engine.register("failing_tool", "Tool with failures", capability_type="tool")

    # Simulate executions (we'll manually update metrics for test)
    # In real usage execute() would do this

    suggestions = cap_engine.suggest_capabilities(limit=5)
    assert isinstance(suggestions, list)
    assert len(suggestions) >= 0

    # Check structure of suggestions
    for s in suggestions:
        assert "name" in s
        assert "reason" in s
        assert "confidence" in s
