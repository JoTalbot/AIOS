#!/usr/bin/env python3
"""
AIOS Demo / Quickstart
======================

This script demonstrates the full AIOS (AI Operating System) capabilities:
- Constitutional evaluation
- Task orchestration
- Memory management (3 categories)
- Knowledge graph
- Reasoning engine
- Learning engine
- Evolution manager (7-stage pipeline)
- MCP Gateway (JSON-RPC 2.0)
- REST API (via AIOSAPI)

Run: python demo.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aios_core import (
    AIOSAPI,
    ConstitutionEngine,
    ConstitutionLoader,
    Database,
    EvolutionManager,
    KnowledgeGraph,
    LearningEngine,
    MemoryManager,
    Orchestrator,
    ReasoningEngine,
    StepStatus,
    TaskStatus,
    TestEngine,
    create_app,
)


def demo_constitutional_evaluation():
    """Demo: Constitutional evaluation with real 67 articles."""
    print("\n" + "=" * 60)
    print("📜 CONSTITUTIONAL EVALUATION")
    print("=" * 60)

    # Use in-memory DB via container override
    from aios_core.container import container
    container.configure(db_path=":memory:")
    db = container.db()
    orch = Orchestrator(db=db)

    # Show constitution stats
    const_stats = orch.policy.engine.constitution.stats()
    print(f"Articles: {const_stats['total_articles']} | Rules: {const_stats['total_rules']}")
    print(f"  MUST: {const_stats['must_count']} | MUST NOT: {const_stats['must_not_count']}")
    print(f"  SHOULD: {const_stats['should_count']} | MAY: {const_stats['may_count']}")

    # Test evaluations
    tests = [
        {
            "name": "✅ Valid low-risk action",
            "action": {
                "goal": "Analyze user behavior patterns",
                "scope": "analytics",
                "risk": "low",
                "audit_log": True,
                "agent_id": "analyst-001",
                "authority": "user",
            },
        },
        {
            "name": "❌ Missing required fields",
            "action": {
                "goal": "Do something",
                "scope": "test",
                "risk": "low",
                # audit_log missing
                "agent_id": "agent-002",
                "authority": "user",
            },
        },
        {
            "name": "❌ Unknown agent blocked",
            "action": {
                "goal": "Access system data",
                "scope": "data",
                "risk": "low",
                "audit_log": True,
                "agent_id": "unknown",
                "authority": "user",
            },
        },
        {
            "name": "⚠️ High risk requires review",
            "action": {
                "goal": "Deploy to production",
                "scope": "production",
                "risk": "high",
                "audit_log": True,
                "agent_id": "deploy-agent",
                "authority": "operator",
            },
        },
        {
            "name": "🚫 Restricted: modify constitution",
            "action": {
                "goal": "Change core law",
                "scope": "constitution",
                "risk": "critical",
                "audit_log": True,
                "agent_id": "admin",
                "authority": "system",
                "action_type": "modify_constitution",
            },
        },
    ]

    for test in tests:
        result = orch.evaluate(test["action"])
        print(f"\n{test['name']}:")
        print(f"  Decision: {result['decision']} | Reason: {result['reason']}")
        if result.get("violations"):
            print(f"  Violations: {len(result['violations'])}")

    print(f"\nTotal evaluations: {orch.policy.stats()['total_executions']}")
    db.close()


def demo_task_orchestration():
    """Demo: Multi-step task orchestration with constitutional checks."""
    print("\n" + "=" * 60)
    print("🎯 TASK ORCHESTRATION")
    print("=" * 60)

    # Use in-memory DB via container override
    from aios_core.container import container
    container.configure(db_path=":memory:")
    db = container.db()
    orch = Orchestrator(db=db)

    # Create a complex task
    task = orch.create_task(
        name="data_analysis_pipeline",
        description="Analyze user behavior and store insights",
        agent_id="pipeline-agent",
        authority="system",
        risk_level="low",
    )

    # Add multiple steps of different types
    steps = [
        (
            "evaluate",
            "read_metrics",
            {
                "goal": "Read user metrics from analytics",
                "scope": "analytics",
                "risk": "low",
            },
        ),
        (
            "memory",
            "store_peak_hours",
            {
                "action": "store",
                "content": {"pattern": "peak_usage_8pm", "confidence": 0.92},
                "category": "operational",
                "tags": ["analytics", "user_behavior", "peak_hours"],
            },
        ),
        (
            "memory",
            "store_user_segments",
            {
                "action": "store",
                "content": {"segments": ["power_users", "casual", "new"], "counts": [120, 450, 80]},
                "category": "operational",
                "tags": ["analytics", "segmentation"],
            },
        ),
        (
            "knowledge",
            "add_insight_node",
            {
                "action": "add_node",
                "label": "peak_usage_pattern",
                "node_type": "insight",
                "properties": {"time": "20:00", "confidence": 0.92, "source": "analytics"},
            },
        ),
        (
            "knowledge",
            "link_to_user_model",
            {
                "action": "add_relation",
                "source_id": "",  # will be filled
                "target_id": "",  # will be filled
                "relation": "informs",
            },
        ),
        (
            "reason",
            "analyze_implications",
            {
                "question": "What does 8pm peak usage imply for resource scaling?",
                "context": {"pattern": "peak_usage_8pm", "confidence": 0.92},
                "use_memory": True,
                "use_knowledge": True,
            },
        ),
        (
            "learn",
            "record_completion",
            {
                "experience": {
                    "task": "data_analysis_pipeline",
                    "insight": "Peak usage at 8pm with 92% confidence",
                    "action": "Scale resources 2x at 19:30-20:30",
                },
                "tags": ["pipeline_success", "resource_planning"],
            },
        ),
    ]

    step_refs = {}
    for step_type, name, params in steps:
        step = orch.add_step(task, step_type, params=params, name=name)
        step_refs[name] = step
        print(f"  Added step: {name} ({step_type})")

    # Execute
    print(f"\nExecuting task '{task.name}'...")
    result = orch.execute_task(task)

    print(f"\nTask Status: {result['status']}")
    print(f"Steps: {result['completed_steps']}/{result['total_steps']} completed")
    for step in result["steps"]:
        cc = step["constitutional_check"]
        print(
            f"  {step['name']}: {step['status']} (constitutional: {cc['decision'] if cc else 'N/A'})"
        )

    # Show final stats
    stats = orch.stats()
    print(f"\nSystem stats:")
    print(f"  Memory: {stats['subsystems']['memory']['total']} items")
    print(f"  Knowledge: {stats['subsystems']['knowledge']['nodes']} nodes")
    print(f"  Learning: {stats['subsystems']['learning']['total_experiences']} experiences")
    print(f"  Constitution evals: {stats['subsystems']['policy']['total_executions']}")

    db.close()


def demo_memory_knowledge():
    """Demo: Memory and Knowledge Graph systems."""
    print("\n" + "=" * 60)
    print("🧠 MEMORY & KNOWLEDGE GRAPH")
    print("=" * 60)

    # Use in-memory DB via container override
    from aios_core.container import container
    container.configure(db_path=":memory:")
    db = container.db()
    orch = Orchestrator(db=db)

    # Memory: 3 constitutional categories
    print("\n📦 Memory (3 categories):")

    # Personal - never federated
    mem1 = orch.memory.store(
        content={"preference": "dark_mode", "language": "en"},
        category="personal",
        tags=["ui", "preferences"],
        source="user_settings",
    )
    print(f"  Personal: {mem1['id'][:8]}... - {mem1['content']}")

    # Operational - system procedures
    mem2 = orch.memory.store(
        content={"procedure": "backup_schedule", "cron": "0 2 * * *"},
        category="operational",
        tags=["ops", "backup"],
        source="ops_manual",
    )
    print(f"  Operational: {mem2['id'][:8]}... - {mem2['content']}")

    # Constitutional - immutable principles
    mem3 = orch.memory.store(
        content={"principle": "Identity immutability", "article": "ARTICLE-I"},
        category="constitutional",
        tags=["identity", "immutable"],
        source="constitution",
    )
    print(f"  Constitutional: {mem3['id'][:8]}... - {mem3['content']}")

    # Search
    results = orch.memory.search(query="procedure", category="operational")
    print(f"\n  Search 'procedure' in operational: {len(results)} results")

    # Knowledge Graph
    print("\n🕸️ Knowledge Graph:")
    n1 = orch.knowledge.add_node("User", "entity", {"type": "actor"})
    n2 = orch.knowledge.add_node("Memory", "entity", {"type": "store"})
    n3 = orch.knowledge.add_node("owns", "relation", {})

    e1 = orch.knowledge.add_relation(n1["id"], n2["id"], "owns", weight=1.0)
    print(f"  Nodes: {orch.knowledge.count_nodes()} | Edges: {orch.knowledge.count_edges()}")

    neighbors = orch.knowledge.neighbors(n1["id"])
    print(f"  Neighbors of 'User': {len(neighbors)}")

    # Stats
    print(f"\n  Memory stats: {orch.memory.stats()}")
    print(f"  KG stats: {orch.knowledge.stats()}")

    db.close()


def demo_reasoning_learning():
    """Demo: Reasoning engine and Learning engine."""
    print("\n" + "=" * 60)
    print("🤔 REASONING & LEARNING")
    print("=" * 60)

    # Use in-memory DB via container override
    from aios_core.container import container
    container.configure(db_path=":memory:")
    db = container.db()
    orch = Orchestrator(db=db)

    # Build reasoning chains
    print("\n🔗 Reasoning Chains:")

    chain1 = orch.reasoning.build_chain(
        question="Why should we scale resources at 8pm?",
        context={"pattern": "peak_usage_8pm", "confidence": 0.92},
        use_memory=True,
        use_knowledge=True,
    )
    print(f"  Q: {chain1['question']}")
    print(f"  Steps: {chain1['step_count']} | Confidence: {chain1['overall_confidence']}")
    print(f"  Conclusion: {chain1['conclusion']}")

    # Learning
    print("\n📚 Learning Engine:")

    learn1 = orch.learning.record(
        {
            "task": "resource_scaling",
            "trigger": "8pm_peak",
            "action": "scale_up_2x",
            "result": "latency_improved_40%",
            "confidence": 0.88,
        }
    )
    print(f"  Recorded: {learn1['id'][:8]}...")

    patterns = orch.learning.extract_patterns()
    print(f"  Successful patterns: {len(patterns)}")

    recs = orch.learning.get_recommendations({"task_name": "resource_scaling"})
    print(f"  Recommendations: {len(recs)}")
    for rec in recs[:2]:
        print(f"    - {rec['action']} (confidence: {rec['confidence']:.2f})")

    db.close()


def demo_evolution():
    """Demo: Evolution Manager - 7-stage pipeline."""
    print("\n" + "=" * 60)
    print("🧬 EVOLUTION MANAGER (7-Stage Pipeline)")
    print("=" * 60)

    # Use in-memory DB via container override
    from aios_core.container import container
    container.configure(db_path=":memory:")
    db = container.db()
    orch = Orchestrator(db=db)

    print("Stages:", " → ".join(orch.evolution.stages))

    # Propose a change
    proposal = orch.evolution.propose(
        change={
            "component": "reasoning_engine",
            "modification": "Add chain-of-thought prompting",
            "expected_improvement": "15% accuracy increase",
        },
        component="reasoning_engine",
        reason="Current reasoning lacks explicit intermediate steps",
    )
    print(f"\n📝 Proposed: {proposal['id'][:8]}... (stage: {proposal['stage']})")

    # Advance through stages
    for i in range(3):
        proposal = orch.evolution.advance(proposal["id"])
        print(f"  Advanced to: {proposal['stage']} ({proposal['status']})")

    # List all
    proposals = orch.evolution.list_proposals()
    print(f"\nTotal proposals: {len(proposals)}")

    stats = orch.evolution.stats()
    print(f"Evolution stats: {stats}")

    db.close()


def demo_mcp_gateway():
    """Demo: MCP Gateway - JSON-RPC 2.0 with constitutional guard."""
    print("\n" + "=" * 60)
    print("🔌 MCP GATEWAY (JSON-RPC 2.0)")
    print("=" * 60)

    from aios_core.mcp.gateway import GatewayConfig, MCPGateway

    gateway = MCPGateway(
        GatewayConfig(
            db_path=":memory:",
            constitution_dir=os.path.join(os.path.dirname(__file__), "docs/constitution"),
            policies_dir=os.path.join(os.path.dirname(__file__), "policies"),
        )
    )

    # Initialize
    init_req = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
    resp = gateway.handle_request(init_req)
    print(f"Initialize: {resp[:100]}...")

    # List tools
    tools_req = '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
    resp = gateway.handle_request(tools_req)
    import json

    data = json.loads(resp)
    print(f"\nAvailable tools: {len(data['result']['tools'])}")
    for tool in data["result"]["tools"]:
        print(f"  - {tool['name']}: {tool['description'][:60]}...")

    # Call a tool (constitutional evaluation)
    eval_req = """{
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "aios_evaluate",
            "arguments": {
                "goal": "Read system metrics",
                "scope": "monitoring",
                "risk": "low"
            }
        }
    }"""
    resp = gateway.handle_request(eval_req)
    data = json.loads(resp)
    print(f"\nTool call result:")
    print(f"  {json.dumps(data['result'], indent=2)[:300]}...")

    # Get stats
    stats_req = '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"aios_stats","arguments":{}}}'
    resp = gateway.handle_request(stats_req)
    data = json.loads(resp)
    print(f"\nGateway stats keys: {list(json.loads(data['result']['content'][0]['text']).keys())}")

    gateway.close()


def demo_rest_api():
    """Demo: REST API via AIOSAPI."""
    print("\n" + "=" * 60)
    print("🌐 REST API (Starlette)")
    print("=" * 60)

    api = AIOSAPI(db_path=":memory:", auth_required=False)

    # Test endpoints
    import asyncio

    from httpx import ASGITransport, AsyncClient

    async def test_api():
        app = api.create_starlette_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Health
            resp = await client.get("/health")
            print(f"GET /health: {resp.json()}")

            # Stats
            resp = await client.get("/api/v1/stats")
            data = resp.json()
            print(
                f"GET /api/v1/stats: version={data.get('version', '9.0.0')}, tasks={data.get('total_tasks', 0)}"
            )

            # Evaluate
            resp = await client.post(
                "/api/v1/evaluate",
                json={
                    "goal": "Test API evaluation",
                    "scope": "api_test",
                    "risk": "low",
                    "audit_log": True,
                },
            )
            print(f"POST /api/v1/evaluate: {resp.json()['decision']}")

            # Memory
            resp = await client.post(
                "/api/v1/memory",
                json={
                    "content": {"test": "api_memory"},
                    "category": "operational",
                    "tags": ["api", "test"],
                },
            )
            print(f"POST /api/v1/memory: {resp.json()['id'][:8]}...")

            resp = await client.get("/api/v1/memory", params={"query": "api_memory"})
            print(f"GET /api/v1/memory?query=api_memory: {resp.json()['count']} results")

            # Knowledge Graph
            resp = await client.post(
                "/api/v1/knowledge/nodes",
                json={
                    "label": "API_Test_Node",
                    "node_type": "test",
                    "properties": {"source": "rest_api"},
                },
            )
            node_id = resp.json()["id"]
            print(f"POST /api/v1/knowledge/nodes: {node_id[:8]}...")

            resp = await client.get(f"/api/v1/knowledge/nodes/{node_id}")
            print(f"GET /api/v1/knowledge/nodes/{{id}}: {resp.json()['label']}")

            # Evolution
            resp = await client.post(
                "/api/v1/evolution/proposals",
                json={
                    "change": {"test": "api_proposal"},
                    "component": "api_demo",
                    "reason": "Testing REST API",
                },
            )
            prop_id = resp.json()["id"]
            print(f"POST /api/v1/evolution/proposals: {prop_id[:8]}...")

            resp = await client.post(f"/api/v1/evolution/proposals/{prop_id}/advance")
            print(f"POST /api/v1/evolution/proposals/{{id}}/advance: stage={resp.json()['stage']}")

            # Tests
            resp = await client.get("/api/v1/tests/suites")
            print(f"GET /api/v1/tests/suites: {len(resp.json()['suites'])} suites")

            resp = await client.post("/api/v1/tests/run")
            print(
                f"POST /api/v1/tests/run: {resp.json()['overall_status']} ({resp.json()['total_tests']} tests)"
            )

            # Audit
            resp = await client.get("/api/v1/audit")
            print(f"GET /api/v1/audit: {resp.json()['count']} events")

            # JSON-RPC bridge
            resp = await client.post(
                "/rpc", json={"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}}
            )
            print(f"POST /rpc (ping): {resp.json()['result']}")

    asyncio.run(test_api())
    api.close()


def demo_test_engine():
    """Demo: Self-test engine."""
    print("\n" + "=" * 60)
    print("🧪 SELF-TEST ENGINE")
    print("=" * 60)

    # Use in-memory DB via container override
    from aios_core.container import container
    container.configure(db_path=":memory:")
    db = container.db()
    engine = TestEngine(
        constitution_dir=os.path.join(os.path.dirname(__file__), "docs/constitution"),
        policies_dir=os.path.join(os.path.dirname(__file__), "policies"),
        db=db,
    )

    print("Available suites:", engine.list_suites())

    # Run all
    print("\nRunning full self-test...")
    report = engine.run_all()

    print(f"\nReport: {report.report_id[:8]}...")
    print(f"  Overall: {report.overall_status}")
    print(
        f"  Total: {report.total_tests} | Passed: {report.total_passed} | Failed: {report.total_failed}"
    )

    # Show summary
    print(f"\n{engine.report_text(report)[:500]}...")

    # Stats
    print(f"\nEngine stats: {engine.stats()}")


def main():
    print(
        """
╔═══════════════════════════════════════════════════════════════╗
║                    AIOS DEMO / QUICKSTART                      ║
║         Self-Evolving Distributed Operating System             ║
║              Powered by Octopus Runtime v3.1.0                 ║
╚═══════════════════════════════════════════════════════════════╝
    """
    )

    demo_constitutional_evaluation()
    demo_task_orchestration()
    demo_memory_knowledge()
    demo_reasoning_learning()
    demo_evolution()
    demo_mcp_gateway()
    demo_rest_api()
    demo_test_engine()

    print("\n" + "=" * 60)
    print("✅ ALL DEMOS COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print(
        """
Next steps:
  • Run MCP Gateway server: python -m aios_core.mcp.gateway
  • Run REST API server: uvicorn aios_core.api.app:create_app --host 0.0.0.0 --port 8000
  • Explore constitution: ls docs/constitution/
  • View policies: cat policies/*.yaml
  • Run tests: python -m pytest tests/ -v
"""
    )


if __name__ == "__main__":
    main()
