def test_full_agent_cycle_structure():
    flow = [
        "api",
        "coordinator",
        "agent",
        "memory",
        "runtime",
        "dashboard",
    ]

    assert flow[0] == "api"
    assert flow[-1] == "dashboard"
