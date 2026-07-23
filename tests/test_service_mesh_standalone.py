"""service_mesh test."""
from aios_core.service_mesh import ServiceMesh
def test_init(): s = ServiceMesh().stats(); assert isinstance(s, dict)
