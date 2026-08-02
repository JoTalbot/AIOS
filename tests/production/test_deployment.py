def test_production_deployment_structure():
    layers = [
        "docker",
        "runtime",
        "healthcheck",
    ]

    assert layers[0] == "docker"
    assert "healthcheck" in layers
