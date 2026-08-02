def test_orchestration_chain():
    chain = [
        "coordinator",
        "scheduler",
        "workflow",
        "agent",
    ]

    assert chain[0] == "coordinator"
    assert chain[-1] == "agent"
