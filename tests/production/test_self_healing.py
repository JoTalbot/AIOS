def test_self_healing_flow():
    flow = [
        "metrics",
        "alert",
        "recovery",
        "restart",
    ]

    assert flow[0] == "metrics"
    assert flow[-1] == "restart"
