#!/usr/bin/env python3
"""
AIOS v4.1 Demo Script
=====================

Demonstrates all major v4.1 features:
- Federation
- ML Planner Scoring
- Multi-Agent Orchestration
- Constitution Evolver
- Capability Marketplace
"""

from aios_core import Database, Orchestrator


def main():
    print("🚀 AIOS v4.1 Demo Starting...\n")

    db = Database(":memory:")
    orch = Orchestrator(db=db)

    # 1. Federation
    print("🌐 Federation Demo")
    node = orch.federation.register_node("demo-node", "http://demo:8000")
    print(f"  Registered node: {node.name}")
    print(f"  Federation stats: {orch.federation.stats()}\n")

    # 2. ML Planner
    print("🧠 ML Planner Scorer Demo")
    plan = orch.planner.create_plan("ml_demo", goal="Optimize workflow")
    orch.planner.add_step(plan, "memory", {"action": "store"})
    orch.planner.add_step(plan, "reason", {})
    score = orch.score_plan_with_ml(plan)
    print(f"  ML Score: {score['ml_score']}")
    print(f"  Features: {score['ml_features']}\n")

    # 3. Multi-Agent
    print("👥 Multi-Agent Demo")
    team = orch.multi_agent.form_team(
        goal="Build report", agents=["researcher", "analyst", "writer"]
    )
    print(f"  Created team: {team.team_id} with {len(team.agents)} agents\n")

    # 4. Constitution Evolver
    print("📜 Constitution Evolver Demo")
    article = orch.constitution_evolver.propose_article(
        "ARTICLE-LXIX — TRANSPARENCY",
        "All decisions must be explainable.",
        ["Log all high-risk actions", "Provide reasoning traces"],
    )
    print(f"  Proposed: {article.title}\n")

    # 5. Marketplace
    print("🛒 Marketplace Demo")
    mp = orch.marketplace
    mp.publish("super_reasoner", "Advanced reasoning", tags=["reasoning"])
    items = mp.search("reasoner")
    print(f"  Found {len(items)} capabilities in marketplace\n")

    print("✅ All v4.1 features demonstrated successfully!")
    print(f"   Version: {orch.version}")
    print(f"   Total subsystems: {len(orch.stats()['subsystems'])}")


if __name__ == "__main__":
    main()
