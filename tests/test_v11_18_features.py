"""Unit tests for AIOS v11.18.0 features: Multi-Tenant Budget Allocation & Swarm Workload Balancing."""

from __future__ import annotations

from aios_core.agent_swarm import AgentRole, AgentSwarm, SwarmAgent, SwarmWorkloadBalancer
from aios_core.multitenancy import MultiTenantBudgetAllocator
from aios_core.substrate_convergence import SubstrateConvergenceEngine
from aios_core.substrate_energy_scheduler import EnergyAwareScheduler


def test_v11_18_multitenant_budget_allocator():
    """Test multi-tenant rolling energy budget allocation and enforcement."""
    allocator = MultiTenantBudgetAllocator(global_limit=100.0, window_seconds=3600.0)

    # Allocate budgets for tenant_a and tenant_b
    allocator.allocate_tenant_budget("tenant_a", limit=20.0)
    allocator.allocate_tenant_budget("tenant_b", limit=50.0)

    assert allocator.can_afford("tenant_a", 15.0) is True
    assert allocator.can_afford("tenant_a", 25.0) is False

    # Record spend for tenant_a
    spend_res = allocator.record_spend("tenant_a", 15.0)
    assert spend_res["global_remaining"] == 85.0
    assert spend_res["tenant_remaining"] == 5.0

    report = allocator.tenant_energy_report()
    assert report["tenants_count"] == 2
    assert "tenant_a" in report["tenant_budgets"]


def test_v11_18_swarm_workload_balancer():
    """Test swarm agent capability-matching, load balancing, and energy routing."""
    swarm = AgentSwarm(name="test_swarm")
    agent1 = SwarmAgent(id="ag1", name="Worker 1", role=AgentRole.WORKER, capabilities=["gpu", "nlp"], reputation=4.0)
    agent2 = SwarmAgent(id="ag2", name="Worker 2", role=AgentRole.WORKER, capabilities=["cpu"], reputation=3.0)

    swarm.add_agent(agent1)
    swarm.add_agent(agent2)

    engine = SubstrateConvergenceEngine()
    engine.register_substrate("sub1", latency_base_ms=10.0, energy_cost_per_unit=1.0, capacity=10)
    scheduler = EnergyAwareScheduler(engine=engine)

    balancer = SwarmWorkloadBalancer(swarm=swarm, scheduler=scheduler)

    tasks = [
        {"id": "t1", "category": "general", "compute_units": 1, "capability_required": "gpu"},
        {"id": "t2", "category": "general", "compute_units": 1, "capability_required": "cpu"},
    ]

    result = balancer.balance_and_assign_tasks(tasks)
    assert result["assigned_count"] == 2
    assert result["unassigned_count"] == 0

    assigned_agents = {a["agent_id"] for a in result["assignments"]}
    assert "ag1" in assigned_agents
    assert "ag2" in assigned_agents

    eff = balancer.efficiency_report()
    assert eff["total_assignments"] == 2
    assert eff["active_agents"] == 2
