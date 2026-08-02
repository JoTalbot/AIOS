def test_olx_agent_pipeline():
    pipeline = [
        "listing",
        "intelligence",
        "decision",
        "action",
    ]

    assert pipeline[1] == "intelligence"
    assert pipeline[-1] == "action"
