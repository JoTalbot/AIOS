"""api_gateway smoke test."""
def test_api_gw(): from aios_core.api_gateway import APIGateway; assert APIGateway() is not None
