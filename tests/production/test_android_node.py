def test_android_node_flow():
    flow = [
        "connector",
        "device",
        "health",
    ]

    assert flow[-1] == "health"
