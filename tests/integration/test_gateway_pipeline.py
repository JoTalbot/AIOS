"""Gateway pipeline smoke tests."""


def test_gateway_import():
    from core.gateway.unified_gateway import UnifiedGateway
    assert UnifiedGateway is not None
