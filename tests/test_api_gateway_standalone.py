"""api_gateway standalone test."""
from aios_core.api_gateway import APIGateway
def test_init(): s = APIGateway().stats(); assert isinstance(s, dict)
