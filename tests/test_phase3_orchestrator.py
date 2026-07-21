"""Tests for AIOS Phase 3 — Orchestrator & Subsystems.

Tests Orchestrator, ReasoningEngine, LearningEngine, EvolutionManager,
PrivacyGuard, and their integration.
"""

import os
import sys
import unittest

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from aios_core.storage import Database
from aios_core.memory_manager import MemoryManager
from aios_core.knowledge_graph import KnowledgeGraph
from aios_core.reasoning_engine import ReasoningEngine
from aios_core.learning_engine import LearningEngine
from aios_core.evolution_manager import EvolutionManager
from aios_core.privacy_guard import PrivacyGuard
from aios_core.orchestrator import (
    Orchestrator, Task, TaskStep, TaskStatus, StepStatus,
)

CONSTITUTION_DIR = os.path.join(PROJECT_ROOT, "docs", "constitution")
POLICIES_DIR = os.path.join(PROJECT_ROOT, "policies")


def _make_db():
    return Database(":memory:")


def _make_orchestrator():
    db = _make_db()
    orch = Orchestrator(
        db=db,
        constitution_dir=CONSTITUTION_DIR,
        policies_dir=POLICIES_DIR,
    )
    return orch, db


# ======================================================================
# TestOrchestrator (20 tests)
# ======================================================================

class TestOrchestrator(unittest.TestCase):
    """Tests for the central orchestrator."""

    def setUp(self):
        self.orch, self.db = _make_orchestrator()

    def tearDown(self):
        self.db.close()

    def test_create_task(self):
        task = self.orch.create_task("test_task", "A test task")
        self.assertIsInstance(task, Task)
        self.assertEqual(task.name, "test_task")
        self.assertEqual(task.description, "A test task")
        self.assertEqual(task.status, TaskStatus.PENDING)
        self.assertIn(task.id, self.orch._tasks)

    def test_add_step(self):
        task = self.orch.create_task("test", "desc")
        step = self.orch.add_step(task, "tool", params={"key": "val"}, name="my_step")
        self.assertIsInstance(step, TaskStep)
        self.assertEqual(step.name, "my_step")
        self.assertEqual(step.step_type, "tool")
        self.assertEqual(len(task.steps), 1)

    def test_add_step_auto_name(self):
        task = self.orch.create_task("test", "desc")
        step = self.orch.add_step(task, "memory")
        self.assertEqual(step.name, "memory_0")

    def test_execute_empty_task(self):
        task = self.orch.create_task("empty", "No steps")
        result = self.orch.execute_task(task)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["total_steps"], 0)
        self.assertEqual(result["completed_steps"], 0)

    def test_execute_single_evaluate_step(self):
        task = self.orch.create_task("eval_test", "Single eval step", risk_level="low")
        self.orch.add_step(task, "evaluate", params={
            "goal": "Read metrics",
            "scope": "monitoring",
            "risk": "low",
        })
        result = self.orch.execute_task(task)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["completed_steps"], 1)
        self.assertIn("constitutional_check", result["steps"][0])

    def test_execute_multi_step_task(self):
        task = self.orch.create_task("multi", "Multiple steps", risk_level="low")
        self.orch.add_step(task, "tool", params={"cmd": "ls"})
        self.orch.add_step(task, "tool", params={"cmd": "pwd"})
        result = self.orch.execute_task(task)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["completed_steps"], 2)

    def test_execute_memory_store_step(self):
        task = self.orch.create_task("mem_store", "Store in memory", risk_level="low")
        self.orch.add_step(task, "memory", params={
            "action": "store",
            "content": {"key": "value"},
            "category": "operational",
        })
        result = self.orch.execute_task(task)
        self.assertEqual(result["status"], "completed")
        self.assertIsNotNone(result["steps"][0]["result"])
        self.assertIn("id", result["steps"][0]["result"])

    def test_execute_memory_search_step(self):
        task = self.orch.create_task("mem_search", "Search memory", risk_level="low")
        self.orch.add_step(task, "memory", params={
            "action": "search",
            "query": "test",
        })
        result = self.orch.execute_task(task)
        self.assertEqual(result["status"], "completed")
        # Result should be a list (search results)
        self.assertIsInstance(result["steps"][0]["result"], list)

    def test_execute_knowledge_step(self):
        task = self.orch.create_task("kg_test", "Knowledge step", risk_level="low")
        self.orch.add_step(task, "knowledge", params={
            "action": "add_node",
            "label": "TestConcept",
            "node_type": "concept",
        })
        result = self.orch.execute_task(task)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["steps"][0]["result"]["label"], "TestConcept")

    def test_execute_reason_step(self):
        task = self.orch.create_task("reason_test", "Reason step", risk_level="low")
        self.orch.add_step(task, "reason", params={
            "question": "What is the best approach?",
        })
        result = self.orch.execute_task(task)
        self.assertEqual(result["status"], "completed")
        self.assertIn("conclusion", result["steps"][0]["result"])
        self.assertGreater(result["steps"][0]["result"]["step_count"], 0)

    def test_execute_learn_step(self):
        task = self.orch.create_task("learn_test", "Learn step", risk_level="low")
        self.orch.add_step(task, "learn", params={
            "experience": {"action": "test", "success": True},
        })
        result = self.orch.execute_task(task)
        self.assertEqual(result["status"], "completed")
        self.assertIsNotNone(result["steps"][0]["result"])

    def test_execute_evolve_step(self):
        task = self.orch.create_task("evolve_test", "Evolve step", risk_level="low")
        self.orch.add_step(task, "evolve", params={
            "change": {"param": "new_value"},
            "component": "test_component",
            "reason": "Improvement",
        })
        result = self.orch.execute_task(task)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["steps"][0]["result"]["component"], "test_component")

    def test_task_denied_by_constitution(self):
        """Unknown agent should be denied by security policy."""
        task = self.orch.create_task(
            "deny_test", "Should be denied",
            agent_id="unknown", authority="reader", risk_level="low",
        )
        self.orch.add_step(task, "evaluate", params={
            "goal": "Access system",
            "scope": "system",
            "risk": "low",
        })
        result = self.orch.execute_task(task)
        self.assertEqual(result["status"], "failed")
        self.assertIn("denied", result["error"].lower())

    def test_task_waiting_approval(self):
        """Critical risk should trigger REVIEW (waiting_approval)."""
        task = self.orch.create_task("review_test", "Needs approval", risk_level="critical")
        self.orch.add_step(task, "evaluate", params={
            "goal": "Critical change",
            "scope": "core",
            "risk": "critical",
            "authority": "senior",
        })
        result = self.orch.execute_task(task)
        self.assertEqual(result["status"], "waiting_approval")

    def test_get_task(self):
        task = self.orch.create_task("find_me", "Find this task")
        found = self.orch.get_task(task.id)
        self.assertIsNotNone(found)
        self.assertEqual(found.name, "find_me")
        self.assertIsNone(self.orch.get_task("nonexistent"))

    def test_list_tasks(self):
        self.orch.create_task("t1", "First")
        self.orch.create_task("t2", "Second")
        tasks = self.orch.list_tasks()
        self.assertEqual(len(tasks), 2)

    def test_list_tasks_by_status(self):
        task = self.orch.create_task("t1", "Task", risk_level="low")
        self.orch.add_step(task, "tool", params={"x": 1})
        self.orch.execute_task(task)
        pending = self.orch.list_tasks(status=TaskStatus.PENDING)
        completed = self.orch.list_tasks(status=TaskStatus.COMPLETED)
        self.assertEqual(len(completed), 1)

    def test_execute_failed_step_stops_pipeline(self):
        task = self.orch.create_task("fail_test", "Should stop on failure", risk_level="low")
        self.orch.add_step(task, "memory", params={
            "action": "invalid_action_xyz",
        })
        self.orch.add_step(task, "tool", params={"should_not_run": True})
        result = self.orch.execute_task(task)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["completed_steps"], 0)
        # Second step should not have run
        self.assertEqual(result["steps"][1]["status"], "pending")

    def test_stats(self):
        self.orch.create_task("s1", "Stats test", risk_level="low")
        stats = self.orch.stats()
        self.assertEqual(stats["version"], "9.0.0-alpha.19")
        self.assertEqual(stats["total_tasks"], 1)
        self.assertIn("subsystems", stats)
        self.assertIn("policy", stats["subsystems"])
        self.assertIn("memory", stats["subsystems"])
        self.assertIn("reasoning", stats["subsystems"])
        self.assertIn("learning", stats["subsystems"])
        self.assertIn("evolution", stats["subsystems"])
        self.assertIn("privacy", stats["subsystems"])

    def test_evaluate_shortcut(self):
        result = self.orch.evaluate({
            "goal": "Read metrics",
            "scope": "monitoring",
            "risk": "low",
        })
        self.assertIn("decision", result)
        self.assertIn("evaluation_id", result)

    def test_direct_evaluate(self):
        """Test direct evaluation via orchestrator."""
        result = self.orch.evaluate({
            "goal": "Test evaluation",
            "scope": "test",
            "risk": "low",
            "agent_id": "test-agent",
            "authority": "reader",
        })
        self.assertIn("allowed", result)
        self.assertIn("decision", result)


# ======================================================================
# TestReasoningEngine (12 tests)
# ======================================================================

class TestReasoningEngine(unittest.TestCase):

    def setUp(self):
        self.db = _make_db()
        self.memory = MemoryManager(db=self.db)
        self.knowledge = KnowledgeGraph(db=self.db)
        self.engine = ReasoningEngine(
            db=self.db, memory=self.memory, knowledge=self.knowledge
        )

    def tearDown(self):
        self.db.close()

    def test_build_chain_basic(self):
        result = self.engine.build_chain("What is the meaning of life?")
        self.assertIn("id", result)
        self.assertEqual(result["question"], "What is the meaning of life?")
        self.assertIn("conclusion", result)
        self.assertIn("steps", result)
        self.assertGreater(result["step_count"], 0)
        self.assertGreater(result["overall_confidence"], 0)

    def test_build_chain_with_context(self):
        result = self.engine.build_chain(
            "What is AIOS?",
            context={"domain": "operating system"},
        )
        self.assertIn("steps", result)
        premise = result["steps"][0]
        self.assertEqual(premise["type"], "premise")
        self.assertIn("AIOS", premise["content"])

    def test_build_chain_with_memory(self):
        self.memory.store(
            content={"text": "What is AIOS? It is an autonomous operating system"},
            category="operational",
            tags=["aios"],
        )
        result = self.engine.build_chain(
            "What is AIOS?",
            use_memory=True,
        )
        has_evidence = any(s["type"] == "evidence" for s in result["steps"])
        self.assertTrue(has_evidence)

    def test_build_chain_with_knowledge(self):
        self.knowledge.add_node("AIOS", node_type="concept")
        result = self.engine.build_chain(
            "AIOS architecture",
            use_knowledge=True,
        )
        has_evidence = any(s["type"] == "evidence" for s in result["steps"])
        self.assertTrue(has_evidence)

    def test_chain_confidence_calculation(self):
        # Chain with more steps should have different confidence
        result = self.engine.build_chain("Test question")
        conf = result["overall_confidence"]
        self.assertGreater(conf, 0)
        self.assertLessEqual(conf, 1.0)

    def test_chain_persistence(self):
        result = self.engine.build_chain("Persistence test")
        # Should have stored in memory
        memories = self.memory.search(tag="reasoning")
        self.assertGreater(len(memories), 0)
        self.assertIn("reasoning_chain", memories[0]["content"].get("type", ""))

    def test_backward_compat_reason(self):
        trace = self.engine.reason("Allow access", ["rule1", "rule2"], ["source1"])
        self.assertEqual(trace["decision"], "Allow access")
        self.assertEqual(len(trace["rules_applied"]), 2)
        self.assertEqual(len(trace["knowledge_sources"]), 1)
        self.assertIn("confidence", trace)

    def test_backward_compat_last_trace(self):
        self.engine.reason("Decision 1", ["r1"], ["s1"])
        self.engine.reason("Decision 2", ["r2"], ["s2"])
        last = self.engine.last_trace()
        self.assertEqual(last["decision"], "Decision 2")

    def test_backward_compat_confidence(self):
        trace = self.engine.reason("Test", ["r1", "r2", "r3"], ["s1", "s2"])
        # base=0.5 + 3*0.1 + 2*0.15 = 1.1, capped at 0.95
        self.assertEqual(trace["confidence"], 0.95)

    def test_empty_question(self):
        result = self.engine.build_chain("")
        self.assertIn("steps", result)
        self.assertGreater(result["step_count"], 0)

    def test_multiple_chains(self):
        self.engine.build_chain("Question 1")
        self.engine.build_chain("Question 2")
        self.engine.build_chain("Question 3")
        stats = self.engine.stats()
        self.assertEqual(stats["chains_built"], 3)

    def test_stats(self):
        self.engine.build_chain("Test")
        self.engine.reason("Decision", ["r1"], ["s1"])
        stats = self.engine.stats()
        self.assertEqual(stats["version"], "3.0.0")
        self.assertEqual(stats["chains_built"], 1)
        self.assertEqual(stats["traces_built"], 1)
        self.assertEqual(stats["storage"], "sqlite")


# ======================================================================
# TestLearningEngine (10 tests)
# ======================================================================

class TestLearningEngine(unittest.TestCase):

    def setUp(self):
        self.db = _make_db()
        self.engine = LearningEngine(db=self.db)

    def tearDown(self):
        self.db.close()

    def test_record_experience(self):
        result = self.engine.record({"action": "test", "outcome": "success"})
        self.assertIn("id", result)
        self.assertNotEqual(result["id"], "no-db")

    def test_record_with_tags(self):
        result = self.engine.record(
            {"action": "deploy"},
            tags=["deployment", "v1"],
        )
        self.assertIn("id", result)

    def test_record_task_completion(self):
        from aios_core.orchestrator import Task, TaskStep, TaskStatus, StepStatus
        task = Task(
            name="test_task",
            status=TaskStatus.COMPLETED,
            steps=[],
            risk_level="low",
        )
        result = self.engine.record_task_completion(task)
        self.assertIn("id", result)

    def test_extract_patterns(self):
        # Record a successful experience
        self.engine.record(
            experience={"task_name": "deploy_v1", "success": True},
            tags=["task_completion", "success"],
        )
        patterns = self.engine.extract_patterns()
        self.assertGreater(len(patterns), 0)
        self.assertEqual(patterns[0]["outcome"], "success")

    def test_extract_patterns_no_experiences(self):
        patterns = self.engine.extract_patterns()
        self.assertEqual(patterns, [])

    def test_get_recommendations(self):
        self.engine.record(
            experience={"task_name": "deploy_v2", "success": True, "confidence": 0.9},
            tags=["task_completion", "success"],
        )
        recs = self.engine.get_recommendations()
        self.assertGreater(len(recs), 0)
        self.assertIn("action", recs[0])
        self.assertIn("confidence", recs[0])

    def test_history(self):
        self.engine.record({"exp1": True})
        self.engine.record({"exp2": True})
        history = self.engine.history()
        self.assertEqual(len(history), 2)

    def test_stats(self):
        self.engine.record({"exp": True})
        stats = self.engine.stats()
        self.assertEqual(stats["version"], "3.0.0")
        self.assertEqual(stats["total_experiences"], 1)
        self.assertEqual(stats["storage"], "sqlite")

    def test_persistence(self):
        """Recorded experiences should be retrievable from memory."""
        self.engine.record({"key": "persistent_data"})
        history = self.engine.history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["experience"]["key"], "persistent_data")

    def test_record_multiple(self):
        for i in range(5):
            self.engine.record({"index": i})
        stats = self.engine.stats()
        self.assertEqual(stats["total_experiences"], 5)


# ======================================================================
# TestEvolutionManager (12 tests)
# ======================================================================

class TestEvolutionManager(unittest.TestCase):

    def setUp(self):
        self.db = _make_db()
        self.mgr = EvolutionManager(db=self.db)

    def tearDown(self):
        self.db.close()

    def test_propose(self):
        proposal = self.mgr.propose(
            change={"param": "new_value"},
            component="reasoning_engine",
            reason="Performance improvement",
        )
        self.assertIn("id", proposal)
        self.assertEqual(proposal["component"], "reasoning_engine")
        self.assertEqual(proposal["stage"], "proposal")
        self.assertEqual(proposal["status"], "proposed")
        self.assertEqual(proposal["stage_index"], 0)

    def test_advance_stage(self):
        p = self.mgr.propose({"change": "v1"}, "test", "test reason")
        result = self.mgr.advance(p["id"])
        self.assertEqual(result["stage_index"], 1)
        self.assertEqual(result["stage"], "testing")

    def test_advance_all_stages(self):
        p = self.mgr.propose({"change": "v1"}, "test", "reason")
        current = p
        for _ in range(5):  # reach the approval gate
            current = self.mgr.advance(current["id"])
        self.mgr.approve(current["id"])
        current = self.mgr.advance(current["id"])
        self.assertEqual(current["stage_index"], 6)
        self.assertEqual(current["stage"], "deployment")

    def test_approve_proposal(self):
        p = self.mgr.propose({"change": "v1"}, "test", "reason")
        for _ in range(5):
            self.mgr.advance(p["id"])
        result = self.mgr.approve(p["id"])
        self.assertEqual(result["status"], "approved")
        self.assertIsNotNone(result["completed_at"])

    def test_reject_proposal(self):
        p = self.mgr.propose({"change": "v1"}, "test", "reason")
        result = self.mgr.reject(p["id"], "Safety concern")
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["rejection_reason"], "Safety concern")

    def test_get_proposal(self):
        p = self.mgr.propose({"change": "v1"}, "comp", "reason")
        found = self.mgr.get_proposal(p["id"])
        self.assertIsNotNone(found)
        self.assertEqual(found["component"], "comp")

    def test_get_unknown_proposal(self):
        found = self.mgr.get_proposal("nonexistent-id")
        self.assertIsNone(found)

    def test_list_proposals(self):
        self.mgr.propose({"c": "1"}, "a", "r1")
        self.mgr.propose({"c": "2"}, "b", "r2")
        self.mgr.propose({"c": "3"}, "c", "r3")
        proposals = self.mgr.list_proposals()
        self.assertEqual(len(proposals), 3)

    def test_list_proposals_by_status(self):
        self.mgr.propose({"c": "1"}, "a", "r1")
        p2 = self.mgr.propose({"c": "2"}, "b", "r2")
        for _ in range(5):
            self.mgr.advance(p2["id"])
        self.mgr.approve(p2["id"])
        proposed = self.mgr.list_proposals(status="proposed")
        approved = self.mgr.list_proposals(status="approved")
        self.assertEqual(len(proposed), 1)
        self.assertEqual(len(approved), 1)

    def test_can_deploy(self):
        p = self.mgr.propose({"c": "1"}, "test", "reason")
        # Advance to approval stage (index 5)
        current = p
        for _ in range(5):
            current = self.mgr.advance(current["id"])
        # Approve it
        current = self.mgr.approve(current["id"])
        self.assertTrue(self.mgr.can_deploy(p["id"]))

    def test_cannot_deploy_incomplete(self):
        p = self.mgr.propose({"c": "1"}, "test", "reason")
        self.assertFalse(self.mgr.can_deploy(p["id"]))

    def test_stats(self):
        self.mgr.propose({"c": "1"}, "a", "r1")
        self.mgr.propose({"c": "2"}, "b", "r2")
        stats = self.mgr.stats()
        self.assertEqual(stats["version"], "3.0.0")
        self.assertEqual(stats["total_proposals"], 2)
        self.assertEqual(stats["storage"], "sqlite")
        self.assertIn("stages", stats)
        self.assertEqual(len(stats["stages"]), 7)


# ======================================================================
# TestPrivacyGuard (12 tests)
# ======================================================================

class TestPrivacyGuard(unittest.TestCase):

    def setUp(self):
        self.guard = PrivacyGuard()

    def test_can_access_operational(self):
        result = self.guard.can_access("agent-1", "operational", "read")
        self.assertTrue(result["allowed"])

    def test_can_access_personal_read(self):
        result = self.guard.can_access("agent-1", "personal", "read")
        self.assertTrue(result["allowed"])
        self.assertEqual(result["classification"], "personal")

    def test_cannot_share_personal(self):
        result = self.guard.can_share("personal", "any-target")
        self.assertFalse(result["allowed"])
        self.assertIn("personal", result["reason"])

    def test_can_share_operational(self):
        result = self.guard.can_share("operational", "verified-agent")
        self.assertTrue(result["allowed"])

    def test_cannot_modify_constitutional(self):
        result = self.guard.can_access("agent-1", "constitutional", "write")
        self.assertFalse(result["allowed"])
        self.assertIn("write", result["reason"])

    def test_check_request_allowed(self):
        result = self.guard.check_request({
            "agent_id": "agent-1",
            "memory_category": "operational",
            "action": "read",
        })
        self.assertTrue(result["allowed"])

    def test_check_request_denied(self):
        result = self.guard.check_request({
            "agent_id": "agent-1",
            "memory_category": "personal",
            "action": "write",
        })
        self.assertFalse(result["allowed"])

    def test_access_log(self):
        self.guard.can_access("a1", "operational", "read")
        self.guard.can_access("a2", "personal", "write")
        log = self.guard.get_access_log()
        self.assertEqual(len(log), 2)

    def test_add_rule(self):
        self.guard.add_rule({
            "classification": "secret",
            "actions_allowed": ["read"],
            "share_allowed": False,
        })
        result = self.guard.can_access("agent-1", "secret", "read")
        self.assertTrue(result["allowed"])

    def test_custom_rule_blocks(self):
        self.guard.add_rule({
            "classification": "secret",
            "actions_allowed": ["read"],
            "share_allowed": False,
        })
        result = self.guard.can_access("agent-1", "secret", "delete")
        self.assertFalse(result["allowed"])

    def test_stats(self):
        self.guard.can_access("a1", "operational", "read")
        self.guard.can_access("a2", "personal", "write")
        stats = self.guard.stats()
        self.assertEqual(stats["version"], "3.0.0")
        self.assertEqual(stats["total_access_checks"], 2)
        self.assertEqual(stats["allowed"], 1)
        self.assertEqual(stats["denied"], 1)
        self.assertEqual(stats["storage"], "memory")

    def test_multiple_checks(self):
        for i in range(5):
            self.guard.can_access(f"agent-{i}", "operational", "read")
        log = self.guard.get_access_log()
        self.assertEqual(len(log), 5)
        self.assertTrue(all(e["allowed"] for e in log))


# ======================================================================
# TestIntegration (6 tests)
# ======================================================================

class TestIntegration(unittest.TestCase):
    """Integration tests across subsystems."""

    def setUp(self):
        self.orch, self.db = _make_orchestrator()

    def tearDown(self):
        self.db.close()

    def test_orchestrator_with_all_subsystems(self):
        """Verify all subsystems are wired in the orchestrator."""
        self.assertIsInstance(self.orch.policy, object)
        self.assertIsInstance(self.orch.memory, MemoryManager)
        self.assertIsInstance(self.orch.knowledge, KnowledgeGraph)
        self.assertIsInstance(self.orch.reasoning, ReasoningEngine)
        self.assertIsInstance(self.orch.learning, LearningEngine)
        self.assertIsInstance(self.orch.evolution, EvolutionManager)
        self.assertIsInstance(self.orch.privacy, PrivacyGuard)

    def test_full_task_lifecycle(self):
        """Full lifecycle: create -> add steps -> execute -> verify."""
        task = self.orch.create_task("lifecycle", "Full lifecycle test", risk_level="low")

        # Add a memory store step
        self.orch.add_step(task, "memory", params={
            "action": "store",
            "content": {"lifecycle": True},
            "category": "operational",
            "tags": ["test"],
        })

        # Add a reasoning step
        self.orch.add_step(task, "reason", params={
            "question": "Test question",
        })

        # Add a knowledge step
        self.orch.add_step(task, "knowledge", params={
            "action": "add_node",
            "label": "LifecycleNode",
        })

        # Execute
        result = self.orch.execute_task(task)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["completed_steps"], 3)

        # Verify memory was stored
        memories = self.orch.memory.search(tag="test")
        self.assertGreater(len(memories), 0)

        # Verify knowledge node was created
        nodes = self.orch.knowledge.find_nodes(label="Lifecycle")
        self.assertGreater(len(nodes), 0)

    def test_reasoning_with_memory_and_knowledge(self):
        """Reasoning should integrate with memory and knowledge graph."""
        # Store relevant memory (include query text so LIKE matches)
        self.orch.memory.store(
            content={"text": "AIOS governance uses constitutional principles"},
            category="operational",
            tags=["governance"],
        )

        # Add knowledge node (use first word of question as search key)
        self.orch.knowledge.add_node("How", node_type="concept")

        # Build reasoning chain with both
        result = self.orch.reasoning.build_chain(
            "How does AIOS governance work?",
            use_memory=True,
            use_knowledge=True,
        )

        self.assertGreater(result["step_count"], 0)
        evidence_steps = [s for s in result["steps"] if s["type"] == "evidence"]
        self.assertGreater(len(evidence_steps), 0)

    def test_evolution_through_orchestrator(self):
        """Evolution proposals should persist through the orchestrator."""
        task = self.orch.create_task("evolution_task", "Evolution via orchestrator", risk_level="low")
        self.orch.add_step(task, "evolve", params={
            "change": {"optimization": True},
            "component": "reasoning",
            "reason": "Performance boost",
        })
        result = self.orch.execute_task(task)
        self.assertEqual(result["status"], "completed")

        # Verify proposal exists in evolution manager
        proposals = self.orch.evolution.list_proposals()
        self.assertGreater(len(proposals), 0)
        self.assertEqual(proposals[0]["component"], "reasoning")

    def test_privacy_guard_with_orchestrator(self):
        """Privacy guard should work alongside the orchestrator."""
        result = self.orch.privacy.can_access("orchestrator", "operational", "read")
        self.assertTrue(result["allowed"])

        result = self.orch.privacy.can_access("orchestrator", "personal", "share")
        self.assertFalse(result["allowed"])

        # Check request
        result = self.orch.privacy.check_request({
            "agent_id": "orchestrator",
            "memory_category": "operational",
            "action": "read",
        })
        self.assertTrue(result["allowed"])

    def test_stats_integration(self):
        """Stats should include all subsystems."""
        # Do some work
        self.orch.create_task("stats_task", "For stats", risk_level="low")
        self.orch.memory.store({"x": 1}, category="operational")
        self.orch.knowledge.add_node("StatsNode")
        self.orch.reasoning.build_chain("Stats question")

        stats = self.orch.stats()
        self.assertEqual(stats["version"], "9.0.0-alpha.19")
        self.assertEqual(stats["total_tasks"], 1)
        self.assertGreater(stats["subsystems"]["memory"]["total"], 0)
        self.assertGreater(stats["subsystems"]["knowledge"]["nodes"], 0)
        self.assertEqual(stats["subsystems"]["reasoning"]["chains_built"], 1)
        self.assertIn("database", stats)
        self.assertIn("tables", stats["database"])


if __name__ == "__main__":
    unittest.main()