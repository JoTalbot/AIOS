"""Tests for auto-scaler, service mesh, and K8s operator."""

from aios_core.auto_scaler import AutoScaler
from aios_core.service_mesh import ServiceMesh
from aios_core.k8s_operator import K8sOperator


def test_auto_scaler_stats():
    s = AutoScaler()
    assert s.stats() is not None


def test_service_mesh_stats():
    sm = ServiceMesh()
    s = sm.stats()
    assert isinstance(s, dict)


def test_k8s_operator_stats():
    ko = K8sOperator()
    s = ko.stats()
    assert isinstance(s, dict)
