"""
AIOS Integration Demo — Full autonomous cycle (Agent → Memory → Evolution → Orchestrator)
Without Octopus integration (~/agents/). Only AIOS internal components.
Based on docs/core/code/*.py modules.
"""

import sys, os, datetime

sys.path.insert(0, os.path.dirname(__file__))

from agent_model import Agent, AgentIdentity, Capability, AgentMemory
from memory_architecture import AIOSMemory, MemoryObservation
from evolution_engine import AIOS_EvolutionEngine
from orchestrator_architecture import (
    AIOS_Orchestrator,
    AIOS_Node,
    MCP_Module,
    WorkerPool,
    ExecutionPlan,
)


def run_autonomous_cycle(goal: str = "observe_application"):
    # 1. Initialize agent
    agent = Agent(
        identity=AgentIdentity("agent_demo_01", "autonomous_agent", datetime.datetime.now()),
        goals=[goal, "learn_from_experience"],
        capabilities=[
            Capability("cap_obs_01", "application_observation", "observe app behavior"),
            Capability("cap_test_01", "application_testing", "run test scenarios"),
        ],
        memory=AgentMemory(),
    )
    print(f"[AGENT] Created: {agent.identity.agent_id} | Goals: {agent.goals}")

    # 2. Agent performs observation (uses memory layer)
    observation_content = f"Application shows standard loading behavior for {goal}"
    agent.memory.short_term.append(observation_content)
    agent.add_experience(observation_content)
    print(f"[AGENT] Experience recorded: {observation_content[:50]}...")

    # 3. Memory architecture forms structured experience
    memory = AIOSMemory()
    obs = MemoryObservation(
        observation_id="obs_demo_01",
        timestamp=datetime.datetime.now(),
        content=observation_content,
        source_agent_id=agent.identity.agent_id,
    )
    memory.observe(obs)
    experience = memory.form_memory([obs], context=goal)
    print(f"[MEMORY] Formed experience: {experience.experience_id}")

    # 4. Evolution engine analyzes and proposes improvement
    evolution = AIOS_EvolutionEngine()
    evolution.record_execution(
        action=goal,
        result="completed_successfully",
        metrics={"efficiency": 0.92, "resource_usage": 0.15},
    )
    proposal = evolution.propose_improvement(
        target="agent_capabilities",
        description="Improve observation speed based on experience",
        reasoning=f"Execution metrics show high efficiency ({0.92}) — capability can be refined.",
    )
    print(f"[EVOLUTION] Proposal: {proposal.proposal_id} | Target: {proposal.target}")

    # 5. Orchestrator coordinates nodes and creates execution plan
    orchestrator = AIOS_Orchestrator()
    orchestrator.register_node(AIOS_Node("node_main", "planner"))
    orchestrator.register_node(AIOS_Node("node_worker_01", "android_testing"))
    orchestrator.register_mcp_module(MCP_Module("mcp_demo_01", "external_access", ["cap_obs_01"]))
    orchestrator.register_worker_pool(
        WorkerPool("pool_demo_01", "node_worker_01", "testing_worker", 3)
    )

    plan = orchestrator.create_plan(
        goal=goal,
        capabilities=["cap_obs_01", "cap_test_01"],
        nodes=["node_main", "node_worker_01"],
        workers=["pool_demo_01"],
    )
    print(
        f"[ORCHESTRATOR] Plan created: {plan.plan_id} | Nodes: {plan.assigned_nodes} | Status: {plan.status}"
    )

    # 6. Agent evolves (adds new capability from proposal)
    agent.evolve(
        {
            "name": proposal.description,
            "description": proposal.expected_impact,
        }
    )
    print(f"[AGENT] Evolved: {len(agent.capabilities)} capabilities total")

    # 7. Final synchronized state (distributed experience)
    sync_state = orchestrator.synchronize_state([node.node_id for node in orchestrator.nodes])
    print(f"[ORCHESTRATOR] Sync: {sync_state['sync_status']} | Nodes: {len(sync_state['nodes'])}")

    # 8. Return complete autonomous cycle result
    return {
        "agent_id": agent.identity.agent_id,
        "experience_id": experience.experience_id,
        "proposal_id": proposal.proposal_id,
        "plan_id": plan.plan_id,
        "capabilities_after_evolution": len(agent.capabilities),
        "cycle_complete": True,
    }


if __name__ == "__main__":
    result = run_autonomous_cycle()
    print("\n=== AUTONOMOUS CYCLE RESULT ===")
    for k, v in result.items():
        print(f"  {k}: {v}")
