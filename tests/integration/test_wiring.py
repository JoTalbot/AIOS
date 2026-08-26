from core.integration.wiring import IntegrationWiring


def test_wiring_register():
    wiring = IntegrationWiring()
    wiring.register("runtime", object())
    assert wiring.get("runtime") is not None
