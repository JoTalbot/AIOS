"""Test continuous autonomous evolution."""
from aios_core.autonomous_evolution import AutonomousEvolution
from aios_core.continuous_learning import ContinuousLearner
def test_evo(): assert AutonomousEvolution().stats() is not None
def test_cl(): assert ContinuousLearner().stats() is not None
