def test_agent_runtime_chain():
    pipeline = [
        "api",
        "agent",
        "memory",
        "runtime",
        "dashboard",
    ]

    assert "memory" in pipeline
    assert pipeline[-1] == "dashboard"
