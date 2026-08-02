def test_api_flow_structure():
    flow = [
        "request",
        "api",
        "coordinator",
        "runtime",
        "result",
    ]

    assert flow[1] == "api"
    assert flow[-1] == "result"
