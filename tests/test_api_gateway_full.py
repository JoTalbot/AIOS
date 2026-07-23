"""API gateway full."""
from aios_core.api_gateway import APIGateway
def test(): s=APIGateway().stats(); assert isinstance(s,dict)
