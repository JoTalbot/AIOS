"""Tests for v3.0 new modules: EventBus, Planner, CapabilityEngine, AutonomyManager, and integration."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aios_core.event_bus import Event, EventBus, EventType
from aios_core.storage import Database


class TestEventBus(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")
        self.bus = EventBus(db=self.db)
        self.received = []

    def tearDown(self):
        self.db.close()

    def test_subscribe_and_emit(self):
        self.bus.subscribe("task_created", lambda e: self.received.append(e))
        event = self.bus.emit("task_created", "test", {"key": "value"})
        self.assertEqual(len(self.received), 1)
        self.assertEqual(self.received[0]["event_type"], "task_created")
        self.assertIn("id", event)

    def test_pattern_subscription(self):
        self.bus.subscribe_pattern("task_*", lambda e: self.received.append(e))
        self.bus.emit("task_created", "test", {})
        self.bus.emit("task_completed", "test", {})
        self.bus.emit("memory_stored", "test", {})
        self.assertEqual(len(self.received), 2)

    def test_unsubscribe(self):
        sub_id = self.bus.subscribe("test", lambda e: self.received.append(e))
        self.bus.unsubscribe(sub_id)
        self.bus.emit("test", "src", {})
        self.assertEqual(len(self.received), 0)

    def test_handler_exception_caught(self):
        def bad_handler(e):
            raise RuntimeError("boom")

        self.bus.subscribe("test", bad_handler)
        event = self.bus.emit("test", "src", {})  # Should not raise
        self.assertIn("id", event)

    def test_persistence(self):
        self.bus.emit("test_event", "test_source", {"data": 123})
        events = self.bus.query(event_type="test_event")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["source"], "test_source")

    def test_query_filters(self):
        self.bus.emit("type_a", "src1", {})
        self.bus.emit("type_b", "src1", {})
        self.bus.emit("type_a", "src2", {})
        results = self.bus.query(event_type="type_a", source="src1")
        self.assertEqual(len(results), 1)

    def test_stats(self):
        self.bus.emit("test", "src", {})
        stats = self.bus.stats()
        self.assertEqual(stats["total_events"], 1)
        self.assertEqual(stats["storage"], "sqlite")

    def test_no_db_fallback(self):
        bus = EventBus()
        event = bus.emit("test", "src", {})
        self.assertIn("id", event)
        self.assertEqual(bus.query(), [])  # No persistence


class TestPlanner(unittest.TestCase):
    def setUp(self):
        from aios_core.planner import Planner

        self.db = Database(":memory:")
        self.planner = Planner(db=self.db)

    def tearDown(self):
        self.db.close()

    def test_create_plan(self):
        plan = self.planner.create_plan("test", "desc", "goal")
        self.assertEqual(plan.name, "test")
        self.assertEqual(plan.status.value, "draft")

    def test_add_step_and_dependency(self):
        plan = self.planner.create_plan("test", "", "goal")
        s1 = self.planner.add_step(plan, "memory", {"action": "store"}, name="store_data")
        s2 = self.planner.add_step(plan, "reason", {}, name="analyze", dependencies=[s1.id])
        self.assertEqual(len(plan.edges), 1)

    def test_validate_no_cycle(self):
        plan = self.planner.create_plan("test", "", "goal")
        s1 = self.planner.add_step(plan, "memory", {}, name="a")
        s2 = self.planner.add_step(plan, "memory", {}, name="b", dependencies=[s1.id])
        result = self.planner.validate_plan(plan)
        self.assertTrue(result["valid"])

    def test_detect_cycle(self):
        plan = self.planner.create_plan("test", "", "goal")
        s1 = self.planner.add_step(plan, "memory", {}, name="a")
        s2 = self.planner.add_step(plan, "memory", {}, name="b", dependencies=[s1.id])
        self.planner.add_dependency(plan, s2.id, s1.id)  # Create cycle: a→b→a
        result = self.planner.validate_plan(plan)
        self.assertFalse(result["valid"])
        self.assertTrue(len(result["errors"]) > 0)

    def test_execution_layers(self):
        plan = self.planner.create_plan("diamond", "", "goal")
        s1 = self.planner.add_step(plan, "memory", {}, name="start")
        s2 = self.planner.add_step(plan, "memory", {}, name="left", dependencies=[s1.id])
        s3 = self.planner.add_step(plan, "memory", {}, name="right", dependencies=[s1.id])
        s4 = self.planner.add_step(plan, "memory", {}, name="end", dependencies=[s2.id, s3.id])
        layers = self.planner.get_execution_layers(plan)
        self.assertEqual(len(layers), 3)  # [start], [left, right], [end]

    def test_mark_step_and_progress(self):
        plan = self.planner.create_plan("test", "", "goal")
        s1 = self.planner.add_step(plan, "memory", {}, name="a")
        s2 = self.planner.add_step(plan, "memory", {}, name="b", dependencies=[s1.id])
        self.planner.mark_step_running(plan, s1.id)
        self.planner.mark_step_completed(plan, s1.id, {"result": "ok"})
        progress = self.planner.get_plan_progress(plan)
        self.assertEqual(progress["completed"], 1)
        self.assertEqual(len(self.planner.get_ready_steps(plan)), 1)

    def test_persistence(self):
        plan = self.planner.create_plan("persist_test", "", "goal")
        self.planner.add_step(plan, "memory", {}, name="step1")
        self.planner.save_plan(plan)
        loaded = self.planner.get_plan(plan.id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.name, "persist_test")


class TestCapabilityEngine(unittest.TestCase):
    def setUp(self):
        from aios_core.capability_engine import CapabilityEngine

        self.db = Database(":memory:")
        self.engine = CapabilityEngine(db=self.db)

    def tearDown(self):
        self.db.close()

    def test_register_and_get(self):
        cap = self.engine.register("test_cap", "A test capability", handler=lambda x: {"ok": True})
        self.assertEqual(cap["name"], "test_cap")
        retrieved = self.engine.get_capability("test_cap")
        self.assertIsNotNone(retrieved)

    def test_discover_and_register(self):
        self.engine.discover("latent_cap", "Not yet ready")
        cap = self.engine.get_capability("latent_cap")
        self.assertEqual(cap["status"], "discovered")

    def test_execute_capability(self):
        self.engine.register("echo", "Echo input", handler=lambda x: x)
        result = self.engine.execute("echo", {"hello": "world"})
        self.assertTrue(result["success"])
        self.assertEqual(result["result"]["hello"], "world")

    def test_lifecycle_transitions(self):
        self.engine.register("cap", "test")
        self.engine.transition("cap", "testing")
        cap = self.engine.get_capability("cap")
        self.assertEqual(cap["status"], "testing")
        # Invalid transition returns success=False
        result = self.engine.transition("cap", "discovered")  # Can't go back
        self.assertFalse(result["success"])

    def test_compose(self):
        self.engine.register(
            "double",
            "Double a number",
            handler=lambda x: {"result": x.get("value", 0) * 2},
        )
        self.engine.register(
            "add_ten",
            "Add 10",
            handler=lambda x: {"result": x.get("result", 0) + 10},
        )
        comp = self.engine.compose(
            "double_then_add",
            [
                {"name": "double", "mapping": {"value": "value"}},
                {"name": "add_ten", "mapping": {"result": "result"}},
            ],
            "Double then add 10",
        )
        result = self.engine.execute("double_then_add", {"value": 5})
        self.assertTrue(result["success"])
        self.assertEqual(result["result"]["result"], 20)  # (5*2)+10

    def test_search(self):
        self.engine.register("tool_a", "Tool A", capability_type="tool", tags=["search"])
        self.engine.register("api_b", "API B", capability_type="api")
        results = self.engine.search(capability_type="tool")
        self.assertEqual(len(results), 1)

    def test_stats(self):
        self.engine.register("stat_cap", "For stats")
        stats = self.engine.stats()
        self.assertEqual(stats["total_capabilities"], 1)
        self.assertEqual(stats["storage"], "sqlite")


class TestAutonomyManager(unittest.TestCase):
    def setUp(self):
        from aios_core.autonomy_manager import AutonomyLevel, AutonomyManager

        self.db = Database(":memory:")
        self.am = AutonomyManager(db=self.db)

    def tearDown(self):
        self.db.close()

    def test_default_level_zero(self):
        result = self.am.check_autonomy("unknown_agent", "low")
        self.assertTrue(result["requires_approval"])

    def test_grant_high_autonomy(self):
        from aios_core.autonomy_manager import AutonomyLevel

        self.am.grant_autonomy("agent_1", AutonomyLevel.LEVEL_4_AUTONOMOUS)
        result = self.am.check_autonomy("agent_1", "high")
        self.assertTrue(result["action_auto_approved"])

    def test_level_3_medium_auto(self):
        from aios_core.autonomy_manager import AutonomyLevel

        self.am.grant_autonomy("agent_2", AutonomyLevel.LEVEL_3_MANAGED)
        result = self.am.check_autonomy("agent_2", "medium")
        self.assertTrue(result["action_auto_approved"])
        result_crit = self.am.check_autonomy("agent_2", "critical")
        self.assertTrue(result_crit["requires_approval"])

    def test_record_and_promote(self):
        from aios_core.autonomy_manager import AutonomyLevel

        self.am.grant_autonomy("agent_3", AutonomyLevel.LEVEL_2_SUPERVISED)
        for _ in range(60):
            self.am.record_action("agent_3", success=True)

        # After auto-adjustment the agent should have been promoted
        profile = self.am.get_profile("agent_3")
        self.assertIsNotNone(profile)
        self.assertGreaterEqual(profile["level"], 3)  # Should be promoted at least to level 3

    def test_record_and_demote(self):
        from aios_core.autonomy_manager import AutonomyLevel

        self.am.grant_autonomy("agent_4", AutonomyLevel.LEVEL_3_MANAGED)
        for i in range(30):
            self.am.record_action("agent_4", success=(i < 10))  # 33% success

        # After auto-adjustment the agent should have been demoted
        profile = self.am.get_profile("agent_4")
        self.assertIsNotNone(profile)
        self.assertLessEqual(profile["level"], 2)  # Should be demoted

    def test_persistence(self):
        from aios_core.autonomy_manager import AutonomyLevel, AutonomyManager

        self.am.grant_autonomy("persist_agent", AutonomyLevel.LEVEL_5_SELF_DIRECTED)
        # Reload
        am2 = AutonomyManager(db=self.db)
        profile = am2.get_profile("persist_agent")
        self.assertIsNotNone(profile)
        self.assertEqual(profile["level"], 5)

    def test_stats(self):
        self.am.grant_autonomy("a1", 2)
        self.am.grant_autonomy("a2", 4)
        stats = self.am.stats()
        self.assertEqual(stats["total_profiles"], 2)


class TestV3Integration(unittest.TestCase):
    def test_orchestrator_with_new_modules(self):
        from aios_core import Database, Orchestrator

        db = Database(":memory:")
        orch = Orchestrator(
            db=db,
            constitution_dir=os.path.join(os.path.dirname(__file__), "..", "docs", "constitution"),
            policies_dir=os.path.join(os.path.dirname(__file__), "..", "policies"),
        )
        # Check new subsystems exist
        self.assertIsNotNone(orch.events)
        self.assertIsNotNone(orch.planner)
        self.assertIsNotNone(orch.capabilities)
        self.assertIsNotNone(orch.autonomy)
        # Execute a task and check events
        task = orch.create_task("integration_test", "V3 integration")
        orch.add_step(
            task,
            "memory",
            params={
                "action": "store",
                "content": {"test": True},
                "category": "operational",
            },
        )
        result = orch.execute_task(task)
        self.assertEqual(result["status"], "completed")
        # Check events were emitted
        events = orch.events.query(event_type="task_created")
        self.assertTrue(len(events) >= 1)
        orch.close()

    def test_enhanced_reasoning(self):
        from aios_core import Database, KnowledgeGraph, MemoryManager, ReasoningEngine

        db = Database(":memory:")
        mm = MemoryManager(db=db)
        kg = KnowledgeGraph(db=db)
        re = ReasoningEngine(db=db, memory=mm, knowledge=kg)
        # Add some knowledge
        n1 = kg.add_node("Python", "language")
        n2 = kg.add_node("AIOS", "system")
        kg.add_relation(n1["id"], n2["id"], "used_in")
        # Test explain method
        chain = re.explain("What is AIOS built with?")
        self.assertIn("steps", chain)
        self.assertTrue(chain["step_count"] > 0)
        db.close()


if __name__ == "__main__":
    unittest.main()
