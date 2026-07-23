"""Service mesh full."""
from aios_core.service_mesh import ServiceMesh
def test(): s=ServiceMesh().stats(); assert isinstance(s,dict)
