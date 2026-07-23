"""API versioning full."""
from aios_core.api_versioning import APIVersioning
def test(): s=APIVersioning().stats(); assert isinstance(s,dict)
