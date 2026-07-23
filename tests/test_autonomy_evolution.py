"""Tests for autonomy management and autonomous evolution."""

from aios_core.autonomy_manager import AutonomyManager
from aios_core.autonomous_evolution import AutonomousEvolution


def test_autonomy_manager_init():
    am = AutonomyManager()
    assert am is not None


def test_autonomy_manager_stats():
    am = AutonomyManager()
    s = am.stats()
    assert isinstance(s, dict)


def test_autonomous_evolution_init():
    ae = AutonomousEvolution()
    assert ae is not None
