from aios.digital_twin.integration import TwinIntegration


def test_twin_integration():
    integration = TwinIntegration()
    integration.register("federation")
    integration.register("meta_kernel")
    integration.publish_state({"healthy": True})
    status = integration.status()
    assert status["components"] == ["federation", "meta_kernel"]
    assert status["state"] == {"healthy": True}
