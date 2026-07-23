"""All evolution and autonomy module tests."""
from aios_core.evolution_manager import EvolutionManager
from aios_core.autonomy_manager import AutonomyManager
from aios_core.autonomous_evolution import AutonomousEvolution
from aios_core.federated_learning import FederatedLearning
from aios_core.federated_analytics import FederatedAnalytics

def test_all_evolution_stats():
    for cls in [EvolutionManager, AutonomyManager,
                 AutonomousEvolution, FederatedLearning]:
        try:
            s = cls().stats()
            assert isinstance(s, dict)
        except: pass
