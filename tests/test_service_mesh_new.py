"""service_mesh test."""
def test(): from aios_core.service_mesh import ServiceMesh; s = ServiceMesh().stats(); assert isinstance(s, dict)
