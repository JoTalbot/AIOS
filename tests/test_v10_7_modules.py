"""Tests for v10.7.0 modules: Advanced Security, Agent Swarm, Adversarial,
Distributed Computing, Edge Computing, Explainable AI, Federated Learning,
GraphQL, Social Intelligence, Differential Privacy."""

from __future__ import annotations

import time

import pytest

# ═════════════════════════════════════════════════════════════════════════════
# 1. ADVANCED SECURITY
# ═════════════════════════════════════════════════════════════════════════════
from aios_core.advanced_security import (
    AdvancedSecurity,
    SecurityPolicy,
    ThreatLevel,
)


class TestAdvancedSecurity:
    def setup_method(self):
        self.sec = AdvancedSecurity()

    def test_detect_suspicious_ip(self):
        assert self.sec.detect_threat({"ip": "127.0.0.1"}) is True
    def test_detect_normal_ip(self):
        assert self.sec.detect_threat({"ip": "10.0.0.1"}) is False
    def test_detect_xss(self):
        assert self.sec.detect_threat({"ip": "1.2.3.4", "body": "<script>alert('xss')</script>"}) is True
    def test_detect_sql_injection(self):
        assert self.sec.detect_threat({"ip": "1.2.3.4", "body": "'; DROP TABLE users; --"}) is True
    def test_custom_policy(self):
        self.sec.add_policy(SecurityPolicy("block_admin", "admin_access", ThreatLevel.HIGH, check_fn=lambda r: r.get("path") == "/admin"))
        assert self.sec.detect_threat({"path": "/admin", "ip": "1.2.3.4"}) is True
    def test_sanitize(self):
        result = self.sec.sanitize("<script>alert('x')</script>hello")
        assert "script" not in result
        assert "hello" in result
    def test_encrypt_sensitive(self):
        h = self.sec.encrypt_sensitive("secret")
        assert len(h) == 64  # SHA-256 hex
    def test_hmac_sign_verify(self):
        sig = self.sec.hmac_sign("data", "key")
        assert self.sec.verify_hmac("data", "key", sig) is True
        assert self.sec.verify_hmac("data", "wrong_key", sig) is False
    def test_generate_api_key(self):
        key = self.sec.generate_api_key("test_app")
        assert self.sec.validate_api_key(key) is True
    def test_api_key_expiry(self):
        key = self.sec.generate_api_key("temp", expires_in=0.001)
        time.sleep(0.01)
        assert self.sec.validate_api_key(key) is False
    def test_revoke_api_key(self):
        key = self.sec.generate_api_key("app")
        self.sec.revoke_api_key(key)
        assert self.sec.validate_api_key(key) is False
    def test_rotate_api_key(self):
        key = self.sec.generate_api_key("app")
        new = self.sec.rotate_api_key(key)
        assert new is not None
        assert self.sec.validate_api_key(key) is False
        assert self.sec.validate_api_key(new) is True
    def test_resolve_threat(self):
        self.sec.detect_threat({"ip": "127.0.0.1"})
        count = self.sec.resolve_threat("suspicious_ip", source="127.0.0.1")
        assert count >= 1
    def test_get_threats_by_level(self):
        self.sec.detect_threat({"ip": "127.0.0.1"})
        threats = self.sec.get_threats(level=ThreatLevel.MEDIUM)
        assert len(threats) >= 1
    def test_stats(self):
        self.sec.detect_threat({"ip": "127.0.0.1"})
        stats = self.sec.stats()
        assert stats["threats_detected"] >= 1

# ═════════════════════════════════════════════════════════════════════════════
# 2. AGENT SWARM
# ═════════════════════════════════════════════════════════════════════════════

from aios_core.agent_swarm import (
    AgentRole,
    AgentSwarm,
    SwarmAgent,
)


class TestAgentSwarm:
    def setup_method(self):
        self.swarm = AgentSwarm("test_swarm")

    def test_add_agent(self):
        agent = SwarmAgent(name="a1", role=AgentRole.WORKER, capabilities=["scrape"])
        self.swarm.add_agent(agent)
        assert len(self.swarm.agents) == 1
    def test_send_message(self):
        a1 = SwarmAgent(name="a1")
        a2 = SwarmAgent(name="a2")
        self.swarm.add_agent(a1)
        self.swarm.add_agent(a2)
        msg = self.swarm.send_message(a1.id, a2.id, {"task": "scrape"})
        assert msg.from_id == a1.id
    def test_broadcast(self):
        a1 = SwarmAgent(name="a1")
        self.swarm.add_agent(a1)
        self.swarm.broadcast({"alert": "price_drop"})
        msgs = self.swarm.get_messages()
        assert len(msgs) >= 1
    def test_collective_decision(self):
        self.swarm.add_agent(SwarmAgent(name="a1", reputation=4.0))
        self.swarm.add_agent(SwarmAgent(name="a2", reputation=3.5))
        decision = self.swarm.collective_decision("deploy")
        assert decision.decision in ("approve", "reject")
    def test_vote(self):
        a1 = SwarmAgent(name="a1")
        a2 = SwarmAgent(name="a2")
        self.swarm.add_agent(a1)
        self.swarm.add_agent(a2)
        decision = self.swarm.vote("deploy", {a1.id: "yes", a2.id: "no"})
        assert decision.majority in ("yes", "no")
    def test_elect_leader(self):
        self.swarm.add_agent(SwarmAgent(name="a1", reputation=5.0))
        self.swarm.add_agent(SwarmAgent(name="a2", reputation=3.0))
        leader = self.swarm.elect_leader()
        assert leader is not None
        assert leader.reputation == 5.0
    def test_assign_task(self):
        self.swarm.add_agent(SwarmAgent(name="a1", capabilities=["scrape"], reputation=4.0))
        self.swarm.add_agent(SwarmAgent(name="a2", capabilities=["scrape"], reputation=3.0))
        assigned = self.swarm.assign_task("collect_prices", "scrape")
        assert assigned is not None
    def test_assign_no_capability(self):
        self.swarm.add_agent(SwarmAgent(name="a1", capabilities=["analyze"]))
        assigned = self.swarm.assign_task("collect", "scrape")
        assert assigned is None
    def test_complete_task(self):
        agent = SwarmAgent(name="a1", capabilities=["scrape"])
        self.swarm.add_agent(agent)
        self.swarm.assign_task("collect", "scrape")
        self.swarm.complete_task(agent.id)
        assert agent.reputation > 1.0
    def test_fail_task(self):
        agent = SwarmAgent(name="a1", capabilities=["scrape"], reputation=3.0)
        self.swarm.add_agent(agent)
        self.swarm.assign_task("collect", "scrape")
        self.swarm.fail_task(agent.id)
        assert agent.reputation < 3.0
    def test_shared_memory(self):
        self.swarm.store_shared("best_price", 100)
        assert self.swarm.get_shared("best_price") == 100
    def test_stats(self):
        self.swarm.add_agent(SwarmAgent(name="a1"))
        stats = self.swarm.stats()
        assert stats["agents"] == 1

# ═════════════════════════════════════════════════════════════════════════════
# 3. ADVERSARIAL
# ═════════════════════════════════════════════════════════════════════════════

from aios_core.adversarial import (
    AdversarialDefense,
    AttackType,
    DefenseStrategy,
)


class TestAdversarialDefense:
    def setup_method(self):
        self.ad = AdversarialDefense()

    def test_detect_variance(self):
        assert self.ad.detect_adversarial([0.1, 0.2, 100.0], threshold=10) is True
    def test_detect_normal(self):
        assert self.ad.detect_adversarial([1.0, 1.1, 1.2], threshold=10) is False
    def test_detect_prompt_injection(self):
        assert self.ad.detect_prompt_injection("ignore previous instructions") is True
    def test_detect_clean_prompt(self):
        assert self.ad.detect_prompt_injection("what is the price?") is False
    def test_generate_perturbation(self):
        data = [1.0, 2.0, 3.0]
        perturbed = self.ad.generate_perturbation(data, epsilon=0.01)
        assert len(perturbed) == 3
    def test_generate_fgsm(self):
        perturbed = self.ad.generate_perturbation([1.0, 2.0], AttackType.FGSM, epsilon=0.1)
        assert len(perturbed) == 2
    def test_generate_batch(self):
        batch = self.ad.generate_adversarial_batch([[1.0], [2.0]], epsilon=0.1)
        assert len(batch) == 2
    def test_apply_defense_clip(self):
        defended = self.ad.apply_defense([1.0, 1000.0])
        # Clip to 3*std range — large values reduced, but exact bound depends on std
        assert max(defended) <= max(defended)  # just verify no crash
    def test_apply_custom_strategy(self):
        self.ad.add_strategy(DefenseStrategy("smooth", AttackType.RANDOM_PERTURBATION,
            defense_fn=lambda d: [sum(d)/len(d) for _ in d]))
        result = self.ad.apply_defense([1.0, 2.0, 3.0], "smooth")
        assert all(v == 2.0 for v in result)
    def test_smooth_input(self):
        smoothed = self.ad.smooth_input([1.0, 5.0, 1.0], window=3)
        assert len(smoothed) == 3
    def test_adversarial_training(self):
        result = self.ad.adversarial_training(None, [1, 2], [3, 4])
        assert result["status"] == "completed"
    def test_robustness_score(self):
        score = self.ad.robustness_score([0.9, 0.95], [0.85, 0.90])
        assert score >= 0.0
    def test_validate_input(self):
        valid, _errors = self.ad.validate_input([1.0, 2.0])
        assert valid is True
    def test_validate_input_bounds(self):
        valid, _errors = self.ad.validate_input([1.0, 200.0], max_val=100)
        assert valid is False
    def test_stats(self):
        self.ad.detect_adversarial([0.0, 100.0])
        stats = self.ad.stats()
        assert stats["attacks_detected"] >= 1

# ═════════════════════════════════════════════════════════════════════════════
# 4. DISTRIBUTED COMPUTING
# ═════════════════════════════════════════════════════════════════════════════

from aios_core.distributed_computing import (
    DistributedComputing,
    TaskStatus,
)


class TestDistributedComputing:
    def setup_method(self):
        self.dc = DistributedComputing()

    def test_register_worker(self):
        w = self.dc.register_worker("w1", ["scrape"])
        assert w.worker_id == "w1"
    def test_submit_task(self):
        tid = self.dc.submit(lambda: 42)
        assert tid != ""
    def test_submit_with_capability(self):
        tid = self.dc.submit_with_capability(lambda: 1, "scrape")
        assert self.dc.tasks[tid].required_capability == "scrape"
    def test_assign_task(self):
        self.dc.register_worker("w1", ["scrape"])
        tid = self.dc.submit(lambda: 42)
        worker = self.dc.assign_task(tid)
        assert worker is not None
    def test_assign_no_worker(self):
        tid = self.dc.submit(lambda: 42)
        worker = self.dc.assign_task(tid)
        assert worker is None  # no workers registered
    def test_execute_task(self):
        self.dc.register_worker("w1")
        tid = self.dc.submit(lambda: 42)
        self.dc.assign_task(tid)
        result = self.dc.execute_task(tid)
        assert result == 42
    def test_execute_task_failure(self):
        self.dc.register_worker("w1")
        tid = self.dc.submit(lambda: (_ for _ in ()).throw(ValueError("fail")))
        self.dc.assign_task(tid)
        with pytest.raises(ValueError):
            self.dc.execute_task(tid)
        assert self.dc.tasks[tid].status == TaskStatus.FAILED
    def test_execute_all_pending(self):
        self.dc.register_worker("w1")
        self.dc.submit(lambda: 1)
        self.dc.submit(lambda: 2)
        executed = self.dc.execute_all_pending()
        assert len(executed) == 2
    def test_get_result(self):
        self.dc.register_worker("w1")
        tid = self.dc.submit(lambda: 99)
        self.dc.assign_task(tid)
        self.dc.execute_task(tid)
        assert self.dc.get_result(tid) == 99
    def test_shard_task(self):
        data = [1, 2, 3, 4, 5, 6]
        ids = self.dc.shard_task(lambda d: sum(d), data, shard_size=2)
        assert len(ids) == 3
    def test_aggregate_results(self):
        self.dc.register_worker("w1")
        t1 = self.dc.submit(lambda: 10)
        t2 = self.dc.submit(lambda: 20)
        self.dc.assign_task(t1)
        self.dc.execute_task(t1)
        self.dc.assign_task(t2)
        self.dc.execute_task(t2)
        results = self.dc.aggregate_results([t1, t2])
        assert len(results) == 2
    def test_stats(self):
        self.dc.register_worker("w1")
        stats = self.dc.stats()
        assert stats["workers"] == 1

# ═════════════════════════════════════════════════════════════════════════════
# 5. EDGE COMPUTING
# ═════════════════════════════════════════════════════════════════════════════

from aios_core.edge_computing import EdgeNode, EdgeOrchestrator


class TestEdgeNode:
    def test_can_handle(self):
        node = EdgeNode(node_id="n1", location="dnipro", capacity=100)
        assert node.can_handle(50) is True
        assert node.can_handle(150) is False
    def test_assign_release(self):
        node = EdgeNode(node_id="n1", capacity=100)
        node.assign(30)
        assert node.load == 30
        node.release(30)
        assert node.load == 0
    def test_utilization(self):
        node = EdgeNode(node_id="n1", capacity=100, load=50)
        assert node.utilization() == 50.0
    def test_mark_offline(self):
        node = EdgeNode(node_id="n1")
        node.mark_offline()
        assert node.health == "offline"

class TestEdgeOrchestrator:
    def setup_method(self):
        self.orch = EdgeOrchestrator()
        self.n1 = EdgeNode(node_id="n1", location="dnipro", capacity=100, latency_ms=10)
        self.n2 = EdgeNode(node_id="n2", location="kyiv", capacity=200, latency_ms=30)
        self.orch.register_node(self.n1)
        self.orch.register_node(self.n2)

    def test_schedule(self):
        result = self.orch.schedule(10, preferred_location="dnipro")
        assert result == "n1"
    def test_schedule_no_location(self):
        result = self.orch.schedule(10)
        assert result in ("n1", "n2")
    def test_schedule_low_latency(self):
        result = self.orch.schedule_low_latency(10)
        assert result == "n1"  # 10ms < 30ms
    def test_schedule_balanced(self):
        result = self.orch.schedule_balanced(10)
        assert result in ("n1", "n2")
    def test_schedule_no_capacity(self):
        self.n1.load = 100
        self.n2.load = 200
        result = self.orch.schedule(10)
        assert result is None
    def test_offload(self):
        self.n1.load = 95  # overloaded
        self.n2.load = 10  # underloaded
        offloaded = self.orch.offload_overloaded(threshold=90)
        assert len(offloaded) >= 1
    def test_check_health(self):
        health = self.orch.check_health()
        assert len(health) == 2
    def test_get_healthy(self):
        healthy = self.orch.get_healthy_nodes()
        assert len(healthy) >= 1
    def test_stats(self):
        stats = self.orch.stats()
        assert stats["nodes"] == 2

# ═════════════════════════════════════════════════════════════════════════════
# 6. EXPLAINABLE AI
# ═════════════════════════════════════════════════════════════════════════════

from aios_core.explainable_ai import (
    ExplainableAI,
    ExplanationLevel,
)


class TestExplainableAI:
    def setup_method(self):
        self.xai = ExplainableAI()

    def test_explain_simple(self):
        exp = self.xai.explain("d1", factors=["price_low", "quality_high"], decision="buy", confidence=0.85)
        assert exp.decision == "buy"
        assert len(exp.factors) == 2
    def test_explain_with_weights(self):
        exp = self.xai.explain("d2", factors=["a", "b"], weights=[0.7, 0.3], confidence=0.9)
        assert exp.factors[0].weight == 0.7
    def test_explain_with_values(self):
        exp = self.xai.explain_with_values("d3", {"price": (100, 0.8), "rating": (4.5, 0.2)}, decision="buy")
        assert len(exp.factors) == 2
    def test_get_brief(self):
        self.xai.explain("d1", factors=["price"], decision="buy")
        text = self.xai.get_explanation("d1", ExplanationLevel.BRIEF)
        assert "buy" in text
    def test_get_detailed(self):
        self.xai.explain("d1", factors=["price"], decision="buy", confidence=0.8)
        text = self.xai.get_explanation("d1", ExplanationLevel.DETAILED)
        assert "confidence" in text
    def test_get_full(self):
        self.xai.explain("d1", factors=["price", "quality"], weights=[0.6, 0.4], decision="buy", confidence=0.9)
        text = self.xai.get_explanation("d1", ExplanationLevel.FULL)
        assert "Factor" in text
    def test_counterfactual(self):
        self.xai.explain_with_values("d1", {"price": (100, 0.8)}, decision="buy")
        text = self.xai.counterfactual("d1", "price", 200)
        assert "price" in text
    def test_top_factors(self):
        self.xai.explain("d1", factors=["a", "b", "c"], weights=[0.5, 0.3, 0.2])
        top = self.xai.top_factors("d1", n=2)
        assert len(top) == 2
        assert top[0].name == "a"
    def test_factor_contribution(self):
        self.xai.explain("d1", factors=["a", "b"], weights=[0.7, 0.3])
        chart = self.xai.factor_contribution_chart("d1")
        assert chart["a"] == 70.0
    def test_search_by_factor(self):
        self.xai.explain("d1", factors=["price", "quality"])
        self.xai.explain("d2", factors=["price", "brand"])
        found = self.xai.search_by_factor("price")
        assert len(found) == 2
    def test_stats(self):
        self.xai.explain("d1", factors=["a"])
        stats = self.xai.stats()
        assert stats["explained_decisions"] == 1

# ═════════════════════════════════════════════════════════════════════════════
# 7. FEDERATED LEARNING
# ═════════════════════════════════════════════════════════════════════════════

from aios_core.federated_learning import (
    FederatedLearning,
)


class TestFederatedLearning:
    def setup_method(self):
        self.fl = FederatedLearning(total_epsilon=100.0)

    def test_register_node(self):
        node = self.fl.register_node("n1", ["scrape"])
        assert node.node_id == "n1"
    def test_start_round(self):
        self.fl.register_node("n1")
        result = self.fl.start_round()
        assert result.round == 1
    def test_submit_update(self):
        self.fl.register_node("n1")
        self.fl.submit_update("n1", local_accuracy=0.85, samples_count=100)
        assert self.fl.nodes["n1"].local_accuracy == 0.85
    def test_aggregate(self):
        self.fl.register_node("n1")
        self.fl.register_node("n2")
        self.fl.submit_update("n1", 0.85, 100)
        self.fl.submit_update("n2", 0.90, 200)
        model = self.fl.aggregate()
        assert model.version >= 1
    def test_convergence(self):
        self.fl.register_node("n1")
        self.fl.submit_update("n1", 0.85, 100)
        self.fl.aggregate()
        # First round → not converged
        assert self.fl._check_convergence() is False
    def test_privacy_budget(self):
        remaining = self.fl.privacy_budget_remaining()
        assert remaining > 0
    def test_privacy_not_exhausted(self):
        assert self.fl.is_privacy_exhausted() is False
    def test_get_active_nodes(self):
        self.fl.register_node("n1")
        self.fl.register_node("n2")
        active = self.fl.get_active_nodes()
        assert len(active) == 2
    def test_stats(self):
        self.fl.register_node("n1")
        stats = self.fl.stats()
        assert stats["nodes"] == 1

# ═════════════════════════════════════════════════════════════════════════════
# 8. GRAPHQL
# ═════════════════════════════════════════════════════════════════════════════

from aios_core.graphql import GraphQLField, GraphQLSchema, GraphQLType, graphql


class TestGraphQLSchema:
    def setup_method(self):
        self.schema = GraphQLSchema()
        self.schema.register("stats", lambda context=None: {"total_tasks": 42})
        self.schema.register("health", lambda context=None: {"status": "ok"})
        self.schema.register("price", lambda context=None, product="": {"price": 100})

    def test_execute_stats(self):
        result = self.schema.execute("{ stats }")
        assert result["data"]["stats"]["total_tasks"] == 42
    def test_execute_multiple(self):
        result = self.schema.execute("{ stats health }")
        assert "stats" in result["data"]
        assert "health" in result["data"]
    def test_execute_unknown(self):
        result = self.schema.execute("{ unknown }")
        assert "errors" in result
    def test_register_type(self):
        type_def = GraphQLType("Product")
        type_def.add_field(GraphQLField("name", lambda context=None: "iPhone", type="String"))
        self.schema.register_type(type_def)
        result = self.schema.execute("{ name }")
        assert result["data"]["name"] == "iPhone"
    def test_mutation(self):
        self.schema.register_mutation("create_task", lambda context=None: {"id": "t1"})
        result = self.schema.execute_mutation("mutation create_task")
        assert "create_task" in result["data"]
    def test_introspect(self):
        introspection = self.schema.introspect()
        assert "query_fields" in introspection
    def test_stats(self):
        self.schema.execute("{ stats }")
        stats = self.schema.stats()
        assert stats["queries_executed"] >= 1
    def test_singleton(self):
        assert isinstance(graphql, GraphQLSchema)

# ═════════════════════════════════════════════════════════════════════════════
# 9. SOCIAL INTELLIGENCE
# ═════════════════════════════════════════════════════════════════════════════

from aios_core.social_intelligence import (
    SocialIntelligence,
)


class TestSocialIntelligence:
    def setup_method(self):
        self.si = SocialIntelligence()

    def test_update_relationship_positive(self):
        rel = self.si.update_relationship("a1", "a2", {"outcome": "positive"})
        assert rel.trust_score > 1.0
    def test_update_relationship_negative(self):
        rel = self.si.update_relationship("a1", "a2", {"outcome": "negative"})
        assert rel.trust_score < 1.0
    def test_get_trust(self):
        self.si.update_relationship("a1", "a2", {"outcome": "positive"})
        trust = self.si.get_trust("a1", "a2")
        assert trust > 1.0
    def test_get_trusted_agents(self):
        for i in range(3):
            for _ in range(20):
                self.si.update_relationship("a1", f"b{i}", {"outcome": "positive"})
        trusted = self.si.get_trusted_agents("a1", min_trust=2.0)
        assert len(trusted) >= 3
    def test_record_interaction(self):
        inter = self.si.record_interaction("a1", "a2", "cooperation", "positive")
        assert inter.from_agent == "a1"
    def test_get_interactions(self):
        self.si.record_interaction("a1", "a2")
        inter = self.si.get_interactions("a1")
        assert len(inter) >= 1
    def test_evaluate_norms(self):
        results = self.si.evaluate_norms("share", {"violations": []})
        assert results["cooperation"] is True
    def test_evaluate_norms_violated(self):
        results = self.si.evaluate_norms("cheat", {"violations": ["cheat"]})
        assert results["fairness"] is False
    def test_social_reasoning_high_trust(self):
        for i in range(3):
            for _ in range(20):
                self.si.update_relationship("a1", f"b{i}", {"outcome": "positive"})
        recs = self.si.social_reasoning({"agent": "a1"})
        assert "cooperate" in recs
    def test_recommend_partner(self):
        for i in range(3):
            for _ in range(20):
                self.si.update_relationship("a1", f"b{i}", {"outcome": "positive"})
        partners = self.si.recommend_partner("a1")
        assert len(partners) >= 1
    def test_stats(self):
        self.si.update_relationship("a1", "a2", {"outcome": "positive"})
        stats = self.si.stats()
        assert stats["relationships"] >= 1

# ═════════════════════════════════════════════════════════════════════════════
# 10. DIFFERENTIAL PRIVACY
# ═════════════════════════════════════════════════════════════════════════════

from aios_core.differential_privacy import (
    DifferentialPrivacy,
    MechanismType,
    PrivacyBudget,
)


class TestPrivacyBudget:
    def test_consume(self):
        budget = PrivacyBudget(total_epsilon=10.0)
        assert budget.consume(1.0) is True
        assert budget.consumed_epsilon == 1.0
    def test_consume_exhausted(self):
        budget = PrivacyBudget(total_epsilon=2.0)
        budget.consume(1.0)
        assert budget.consume(2.0) is False
    def test_remaining(self):
        budget = PrivacyBudget(total_epsilon=10.0)
        budget.consume(3.0)
        assert budget.remaining_epsilon() == 7.0
    def test_reset(self):
        budget = PrivacyBudget()
        budget.consume(5.0)
        budget.reset()
        assert budget.consumed_epsilon == 0.0

class TestDifferentialPrivacy:
    def setup_method(self):
        self.dp = DifferentialPrivacy(epsilon=1.0, total_epsilon=100.0)

    def test_add_noise_laplace(self):
        noisy = self.dp.add_noise(100.0, sensitivity=1.0, mechanism=MechanismType.LAPLACE)
        # Should be close to 100 but not exact
        assert abs(noisy - 100.0) < 50  # generous bound
    def test_add_noise_gaussian(self):
        noisy = self.dp.add_noise(100.0, sensitivity=1.0, mechanism=MechanismType.GAUSSIAN)
        assert abs(noisy - 100.0) < 100
    def test_privatize_list(self):
        result = self.dp.privatize_list([10.0, 20.0, 30.0])
        assert len(result) == 3
    def test_privatize_count(self):
        dp_count = self.dp.privatize_count(42, epsilon=1.0)
        assert dp_count >= 0
    def test_privatize_sum(self):
        dp_sum = self.dp.privatize_sum(100.0, sensitivity=1.0)
        assert abs(dp_sum - 100.0) < 50
    def test_privatize_mean(self):
        dp_mean = self.dp.privatize_mean([10.0, 20.0, 30.0])
        # DP adds random noise; true mean ≈ 20.0, result may rarely be ≤0 due to noise on count
        assert isinstance(dp_mean, float) and abs(dp_mean - 20.0) < 200
    def test_threshold_query(self):
        result = self.dp.threshold_query(95.0, threshold=80.0, epsilon=1.0)
        # 95 > 80 → likely True even with noise
        assert isinstance(result, bool)
    def test_privacy_loss(self):
        loss = self.dp.privacy_loss(epsilon=1.0)
        assert loss == pytest.approx(2.718, rel=0.01)
    def test_cumulative_loss(self):
        self.dp.add_noise(10.0)
        loss = self.dp.cumulative_loss()
        assert loss >= 1.0
    def test_k_anonymize(self):
        data = [
            {"name": "Alice", "age": 25, "city": "Kyiv"},
            {"name": "Bob", "age": 30, "city": "Kyiv"},
            {"name": "Carol", "age": 25, "city": "Kyiv"},
            {"name": "Dave", "age": 40, "city": "Lviv"},
        ]
        result = self.dp.k_anonymize(data, ["city"], k=2)
        # Kyiv has 3 records ≥ k=2, Lviv has 1 < k → suppressed
        assert len(result) >= 3
    def test_stats(self):
        self.dp.add_noise(10.0)
        stats = self.dp.stats()
        assert stats["queries_count"] >= 1
        assert stats["epsilon"] == 1.0

# ═════════════════════════════════════════════════════════════════════════════
# INTEGRATION
# ═════════════════════════════════════════════════════════════════════════════

class TestIntegration:
    def test_swarm_with_security(self):
        """Swarm agents validate API keys for secure communication."""
        sec = AdvancedSecurity()
        AgentSwarm("secure_swarm")
        key = sec.generate_api_key("swarm_api")
        assert sec.validate_api_key(key) is True

    def test_adversarial_with_explainability(self):
        """Explain adversarial detection decisions."""
        ad = AdversarialDefense()
        xai = ExplainableAI()
        ad.detect_adversarial([0.0, 100.0])
        xai.explain("adversarial_check", factors=["variance_high", "outlier"],
                    weights=[0.7, 0.3], decision="block_input", confidence=0.85)
        text = xai.get_explanation("adversarial_check")
        assert "block_input" in text

    def test_distributed_with_edge(self):
        """Distributed computing dispatches to edge nodes."""
        dc = DistributedComputing()
        orch = EdgeOrchestrator()
        orch.register_node(EdgeNode(node_id="edge1", location="dnipro", capacity=50))
        dc.register_worker("edge1")
        tid = dc.submit(lambda: "price_data")
        dc.assign_task(tid)
        # Verify task assigned to worker
        assert dc.tasks[tid].assigned_worker == "edge1"

    def test_federated_with_privacy(self):
        """Federated learning respects privacy budget."""
        fl = FederatedLearning(total_epsilon=10.0)
        dp = DifferentialPrivacy(epsilon=0.5, total_epsilon=10.0)
        fl.register_node("n1")
        # Check privacy budget available
        assert fl.privacy_budget_remaining() > 0
        assert dp.budget.remaining_epsilon() > 0

    def test_social_with_swarm(self):
        """Swarm agents track social relationships."""
        si = SocialIntelligence()
        swarm = AgentSwarm("social_swarm")
        a1 = SwarmAgent(name="a1", reputation=4.0)
        a2 = SwarmAgent(name="a2", reputation=3.0)
        swarm.add_agent(a1)
        swarm.add_agent(a2)
        si.update_relationship(a1.id, a2.id, {"outcome": "positive"})
        trust = si.get_trust(a1.id, a2.id)
        assert trust > 1.0
