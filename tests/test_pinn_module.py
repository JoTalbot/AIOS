"""Tests for aios_core/pinn.py"""
from __future__ import annotations
import pytest
from aios_core.pinn import PINN


@pytest.fixture()
def pinn():
    return PINN(pde="heat", boundary_conditions=[], domain=(0, 1))


class TestPINN:
    def test_create(self, pinn):
        assert pinn is not None

    def test_generate_collocation(self, pinn):
        points = pinn.generate_collocation(n_points=10)
        assert isinstance(points, list)

    def test_add_boundary(self, pinn):
        pinn.add_boundary(name="left", condition_type="dirichlet", location=0.0, value=0.0)

    def test_compute_residual(self, pinn):
        result = pinn.compute_residual(x=[0.5])
        assert isinstance(result, (float, list, dict))

    def test_compute_total_residual(self, pinn):
        result = pinn.compute_total_residual()
        assert isinstance(result, (float, dict))

    def test_stats(self, pinn):
        s = pinn.stats()
        assert isinstance(s, dict)
