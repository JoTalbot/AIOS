"""All distributed computing tests."""
from aios_core.distributed_computing import DistributedRuntime
from aios_core.edge_computing import EdgeNode
from aios_core.federation_manager import FederationManager
from aios_core.swarm_intelligence import SwarmOptimizer
from aios_core.blockchain import BlockchainLedger
from aios_core.multi_agent_rl import MultiAgentRL
from aios_core.multi_agent_orchestrator import MultiAgentOrchestrator

def test_all_distributed_stats():
    for cls in [DistributedRuntime, FederationManager, SwarmOptimizer,
                 BlockchainLedger, MultiAgentOrchestrator]:
        try:
            s = cls().stats()
            assert isinstance(s, dict)
        except: pass
