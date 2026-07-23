"""Test API gateway and versioning."""
from aios_core.api.gateway import APIGateway
from aios_core.api_versioning import APIVersioning
def test_gateway(): assert APIGateway is not None
def test_versioning(): assert APIVersioning is not None
