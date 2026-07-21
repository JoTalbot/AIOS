"""Tests for AIOS Constitution-Runtime Bridge v3.0.0

Tests ConstitutionLoader, PolicyLoader, ConstitutionEngine,
ConstitutionValidator, and RuntimePolicy with real project files.
"""

import os
import sys
import unittest

# Ensure the project root is on the path
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from aios_core.constitution_loader import (
    ConstitutionLoader,
    ObligationLevel,
    _roman_to_int,
    _detect_obligation,
)
from aios_core.policy_loader import (
    PolicyLoader,
    PolicyValidationError,
)
from aios_core.constitution_engine import ConstitutionEngine, DecisionOutcome
from aios_core.constitution_validator import ConstitutionValidator
from aios_core.runtime_policy import RuntimePolicy

# Paths to real project data
CONSTITUTION_DIR = os.path.join(PROJECT_ROOT, "docs", "constitution")
POLICIES_DIR = os.path.join(PROJECT_ROOT, "policies")


# ======================================================================
# ConstitutionLoader Tests
# ======================================================================

class TestRomanConversion(unittest.TestCase):
    """Test Roman numeral conversion utility."""

    def test_simple_numerals(self):
        self.assertEqual(_roman_to_int("I"), 1)
        self.assertEqual(_roman_to_int("V"), 5)
        self.assertEqual(_roman_to_int("X"), 10)
        self.assertEqual(_roman_to_int("L"), 50)
        self.assertEqual(_roman_to_int("C"), 100)

    def test_subtractive(self):
        self.assertEqual(_roman_to_int("IV"), 4)
        self.assertEqual(_roman_to_int("IX"), 9)
        self.assertEqual(_roman_to_int("XL"), 40)
        self.assertEqual(_roman_to_int("XC"), 90)

    def test_compound(self):
        self.assertEqual(_roman_to_int("VIII"), 8)
        self.assertEqual(_roman_to_int("XXXVI"), 36)
        self.assertEqual(_roman_to_int("LXVII"), 67)


class TestObligationDetection(unittest.TestCase):
    """Test obligation keyword detection."""

    def test_must(self):
        self.assertEqual(_detect_obligation("AIOS MUST protect"), ObligationLevel.MUST)

    def test_must_not(self):
        self.assertEqual(_detect_obligation("AIOS MUST NOT modify"), ObligationLevel.MUST_NOT)

    def test_may(self):
        self.assertEqual(_detect_obligation("AIOS MAY develop"), ObligationLevel.MAY)

    def test_should(self):
        self.assertEqual(_detect_obligation("AIOS SHOULD improve"), ObligationLevel.SHOULD)

    def test_should_not(self):
        self.assertEqual(_detect_obligation("AIOS SHOULD NOT exceed"), ObligationLevel.SHOULD_NOT)

    def test_unknown(self):
        self.assertEqual(_detect_obligation("Some random text"), ObligationLevel.UNKNOWN)

    def test_must_not_priority_over_must(self):
        self.assertEqual(
            _detect_obligation("AIOS MUST NOT MUST do something"),
            ObligationLevel.MUST_NOT,
        )


class TestConstitutionLoader(unittest.TestCase):
    """Test loading real constitutional articles."""

    @classmethod
    def setUpClass(cls):
        cls.loader = ConstitutionLoader(CONSTITUTION_DIR)

    def test_loads_all_articles(self):
        """67 articles should be loaded."""
        self.assertGreaterEqual(len(self.loader.articles), 60)

    def test_articles_have_ids(self):
        for article_id in self.loader.articles:
            self.assertTrue(article_id.startswith("ARTICLE-"))

    def test_rules_extracted(self):
        """Constitution should have MUST/MUST NOT rules."""
        stats = self.loader.stats()
        self.assertGreater(stats["must_count"], 50)
        self.assertGreater(stats["must_not_count"], 20)

    def test_get_article(self):
        article = self.loader.get_article("ARTICLE-V")
        self.assertIsNotNone(article)
        self.assertEqual(article.title, "Security")
        self.assertIn("Immutable", article.status)

    def test_get_must_rules(self):
        rules = self.loader.get_must_rules()
        self.assertTrue(all(r.obligation == ObligationLevel.MUST for r in rules))
        self.assertTrue(len(rules) > 50)

    def test_get_must_not_rules(self):
        rules = self.loader.get_must_not_rules()
        self.assertTrue(all(r.obligation == ObligationLevel.MUST_NOT for r in rules))
        self.assertTrue(len(rules) > 20)

    def test_search_rules(self):
        """Search for 'security' should return relevant rules."""
        results = self.loader.search_rules("security")
        self.assertGreater(len(results), 5)

    def test_rules_for_topic(self):
        """Topic search should find rules about autonomy."""
        results = self.loader.rules_for_topic("autonomy")
        self.assertGreater(len(results), 3)

    def test_stats(self):
        stats = self.loader.stats()
        self.assertIn("total_articles", stats)
        self.assertIn("total_rules", stats)
        self.assertIn("must_count", stats)

    def test_article_v_has_sections(self):
        """Article V (Security) should have sections like 'Law of Integrity Protection'."""
        article = self.loader.get_article("ARTICLE-V")
        self.assertIsNotNone(article)
        self.assertGreater(len(article.sections), 5)

    def test_article_viii_autonomy(self):
        """Article VIII (Autonomy) should have rules about bounded autonomy."""
        article = self.loader.get_article("ARTICLE-VIII")
        self.assertIsNotNone(article)
        self.assertGreater(len(article.rules), 5)

    def test_check_action_returns_list(self):
        action = {
            "goal": "test",
            "scope": "system",
            "risk": "low",
            "audit_log": True,
            "action_type": "modify_security",
        }
        results = self.loader.check_action(action)
        self.assertIsInstance(results, list)


# ======================================================================
# PolicyLoader Tests
# ======================================================================

class TestPolicyLoader(unittest.TestCase):
    """Test loading real YAML policies."""

    @classmethod
    def setUpClass(cls):
        cls.loader = PolicyLoader(POLICIES_DIR)

    def test_loads_all_policies(self):
        self.assertEqual(len(self.loader.policies), 3)

    def test_policy_names(self):
        names = self.loader.list_policies()
        self.assertIn("security_policy", names)
        self.assertIn("federation_policy", names)
        self.assertIn("evolution_policy", names)

    def test_security_policy_threat_levels(self):
        sec = self.loader.get_security_policy()
        self.assertIsNotNone(sec)
        self.assertIn("critical", sec.threat_levels)
        self.assertIn("low", sec.threat_levels)
        self.assertEqual(sec.threat_levels["critical"].escalation, "human_review")
        self.assertEqual(sec.threat_levels["low"].escalation, "background_monitoring")

    def test_evolution_policy_stages(self):
        stages = self.loader.get_evolution_stages()
        self.assertIn("sandbox_testing", stages)
        self.assertIn("deployment", stages)
        self.assertEqual(len(stages), 6)

    def test_evolution_policy_restrictions(self):
        restrictions = self.loader.get_evolution_restrictions()
        self.assertIn("direct_core_modification", restrictions)
        self.assertEqual(restrictions["direct_core_modification"], "prohibited")

    def test_is_rule_enabled(self):
        self.assertTrue(self.loader.is_rule_enabled("security_policy", "least_privilege"))
        self.assertTrue(self.loader.is_rule_enabled("security_policy", "unknown_access_blocked"))

    def test_is_requirement_met(self):
        self.assertTrue(self.loader.is_requirement_met("security_policy", "audit_logging"))
        self.assertIsNone(self.loader.is_requirement_met("security_policy", "nonexistent"))

    def test_get_threat_action(self):
        self.assertEqual(self.loader.get_threat_action("critical"), "immediate_isolation")
        self.assertEqual(self.loader.get_threat_action("low"), "standard_operation")
        self.assertIsNone(self.loader.get_threat_action("nonexistent"))

    def test_federation_policy(self):
        fed = self.loader.get_federation_policy()
        self.assertIsNotNone(fed)
        self.assertTrue(self.loader.is_rule_enabled("federation_policy", "verified_nodes_only"))

    def test_stats(self):
        stats = self.loader.stats()
        self.assertEqual(stats["total_policies"], 3)


# ======================================================================
# ConstitutionEngine Tests
# ======================================================================

class TestConstitutionEngine(unittest.TestCase):
    """Test constitution evaluation with real data."""

    @classmethod
    def setUpClass(cls):
        cls.engine = ConstitutionEngine(CONSTITUTION_DIR, POLICIES_DIR)

    def test_valid_action_allowed(self):
        """Valid low-risk action with all requirements met should be ALLOWed."""
        result = self.engine.evaluate({
            "goal": "Read system metrics",
            "scope": "monitoring",
            "risk": "low",
            "audit_log": True,
            "agent_id": "monitor-agent-01",
            "authority": "reader",
        })
        self.assertEqual(result["decision"], "ALLOW")

    def test_missing_fields_denied(self):
        """Action without required fields should be DENYed."""
        result = self.engine.evaluate({
            "goal": "test",
        })
        self.assertEqual(result["decision"], "DENY")
        self.assertEqual(result["reason"], "missing_required_fields")

    def test_no_audit_log_denied(self):
        """Missing audit_log triggers constitutional violation."""
        result = self.engine.evaluate({
            "goal": "Do something",
            "scope": "system",
            "risk": "low",
            "audit_log": False,
        })
        self.assertEqual(result["decision"], "DENY")

    def test_high_risk_review(self):
        """High risk should trigger REVIEW."""
        result = self.engine.evaluate({
            "goal": "Deploy new module",
            "scope": "production",
            "risk": "high",
            "audit_log": True,
            "authority": "operator",
        })
        self.assertEqual(result["decision"], "REVIEW")

    def test_critical_risk_review(self):
        """Critical risk should trigger REVIEW."""
        result = self.engine.evaluate({
            "goal": "Emergency change",
            "scope": "core",
            "risk": "critical",
            "audit_log": True,
            "authority": "senior_operator",
        })
        self.assertIn(result["decision"], ("REVIEW", "DENY"))

    def test_restricted_action_modify_constitution(self):
        """Modifying constitution should trigger REVIEW."""
        result = self.engine.evaluate({
            "goal": "Update article text",
            "scope": "constitution",
            "risk": "high",
            "audit_log": True,
            "action_type": "modify_constitution",
        })
        self.assertEqual(result["decision"], "REVIEW")
        self.assertEqual(result["reason"], "restricted_action")
        self.assertIn("ARTICLE-I", result.get("matched_articles", []))

    def test_restricted_action_destroy_records(self):
        """Destroying records should trigger REVIEW."""
        result = self.engine.evaluate({
            "goal": "Clean up old records",
            "scope": "memory",
            "risk": "medium",
            "audit_log": True,
            "action_type": "destroy_records",
        })
        self.assertEqual(result["decision"], "REVIEW")

    def test_unknown_agent_blocked(self):
        """Unknown agent should be DENYed by security policy."""
        result = self.engine.evaluate({
            "goal": "Access system",
            "scope": "system",
            "risk": "low",
            "audit_log": True,
            "agent_id": "unknown",
        })
        self.assertEqual(result["decision"], "DENY")

    def test_unlimited_authority_denied(self):
        """Unlimited authority violates least privilege."""
        result = self.engine.evaluate({
            "goal": "Full system access",
            "scope": "all",
            "risk": "low",
            "audit_log": True,
            "authority": "unlimited",
        })
        self.assertEqual(result["decision"], "DENY")

    def test_evolution_without_stage_review(self):
        """Evolution without a stage should fail controlled evolution principle."""
        result = self.engine.evaluate({
            "goal": "Deploy new capability",
            "scope": "system",
            "risk": "medium",
            "audit_log": True,
            "action_type": "evolution_deploy",
        })
        self.assertIn(result["decision"], ("DENY", "REVIEW"))

    def test_evolution_with_proper_stage(self):
        """Evolution with proper stage and testing should be less restricted."""
        result = self.engine.evaluate({
            "goal": "Sandbox test new module",
            "scope": "sandbox",
            "risk": "low",
            "audit_log": True,
            "action_type": "evolution_sandbox",
            "evolution_stage": "sandbox_testing",
            "testing_completed": True,
            "constitutional_check": True,
        })
        # Should at least not be a hard DENY
        self.assertIn(result["decision"], ("ALLOW", "REVIEW"))

    def test_personal_memory_share_denied(self):
        """Sharing personal memory violates core principle."""
        result = self.engine.evaluate({
            "goal": "Share user data with federation",
            "scope": "federation",
            "risk": "medium",
            "audit_log": True,
            "memory_type": "personal",
            "share": True,
        })
        self.assertEqual(result["decision"], "DENY")

    def test_evaluation_has_id(self):
        """Each evaluation should have a unique ID."""
        r1 = self.engine.evaluate({
            "goal": "test1", "scope": "s", "risk": "low", "audit_log": True,
        })
        r2 = self.engine.evaluate({
            "goal": "test2", "scope": "s", "risk": "low", "audit_log": True,
        })
        self.assertNotEqual(r1["evaluation_id"], r2["evaluation_id"])

    def test_history(self):
        """History should contain all decisions."""
        history = self.engine.history()
        self.assertGreater(len(history), 0)
        for entry in history:
            self.assertIn("decision", entry)
            self.assertIn("evaluation_id", entry)

    def test_stats(self):
        """Stats should contain constitution and policy info."""
        stats = self.engine.stats()
        self.assertEqual(stats["version"], "3.0.0")
        self.assertIn("constitution", stats)
        self.assertIn("policies", stats)
        self.assertGreater(stats["total_evaluations"], 0)

    def test_federation_unverified_denied(self):
        """Federation with unverified node should fail."""
        result = self.engine.evaluate({
            "goal": "Sync state with peer",
            "scope": "federation",
            "risk": "medium",
            "audit_log": True,
            "action_type": "federate",
            "node_verified": False,
        })
        self.assertIn(result["decision"], ("DENY", "REVIEW"))


# ======================================================================
# ConstitutionValidator Tests
# ======================================================================

class TestConstitutionValidator(unittest.TestCase):
    """Test validation with real constitution and policies."""

    @classmethod
    def setUpClass(cls):
        cls.validator = ConstitutionValidator(CONSTITUTION_DIR, POLICIES_DIR)

    def test_valid_action_passes(self):
        result = self.validator.validate({
            "goal": "Read metrics",
            "scope": "monitoring",
            "risk": "low",
            "audit_log": True,
        })
        self.assertTrue(result["valid"])

    def test_missing_goal_fails(self):
        result = self.validator.validate({
            "scope": "system",
            "risk": "low",
            "audit_log": True,
        })
        self.assertFalse(result["valid"])
        codes = [e["code"] for e in result["errors"]]
        self.assertIn("missing_goal", codes)

    def test_invalid_risk_level(self):
        result = self.validator.validate({
            "goal": "test",
            "scope": "system",
            "risk": "extreme",
            "audit_log": True,
        })
        self.assertFalse(result["valid"])
        codes = [e["code"] for e in result["errors"]]
        self.assertIn("invalid_risk_level", codes)

    def test_personal_memory_share_error(self):
        result = self.validator.validate({
            "goal": "Share user data",
            "scope": "federation",
            "risk": "medium",
            "audit_log": True,
            "memory_type": "personal",
            "share": True,
        })
        self.assertFalse(result["valid"])
        codes = [e["code"] for e in result["errors"]]
        self.assertIn("memory_separation_violation", codes)

    def test_invalid_evolution_stage(self):
        result = self.validator.validate({
            "goal": "Deploy",
            "scope": "system",
            "risk": "medium",
            "audit_log": True,
            "action_type": "evolution_deploy",
            "evolution_stage": "invalid_stage",
        })
        self.assertFalse(result["valid"])
        codes = [e["code"] for e in result["errors"]]
        self.assertIn("invalid_evolution_stage", codes)

    def test_no_audit_log_error(self):
        result = self.validator.validate({
            "goal": "test",
            "scope": "system",
            "risk": "low",
            "audit_log": False,
        })
        self.assertFalse(result["valid"])
        codes = [e["code"] for e in result["errors"]]
        self.assertIn("security_audit_logging", codes)

    def test_warnings_for_high_risk(self):
        result = self.validator.validate({
            "goal": "Deploy",
            "scope": "production",
            "risk": "high",
            "audit_log": True,
        })
        codes = [w["code"] for w in result["warnings"]]
        self.assertIn("high_risk_no_authority", codes)

    def test_report(self):
        report = self.validator.report()
        self.assertIn("total_validations", report)
        self.assertIn("success_rate", report)

    def test_result_structure(self):
        result = self.validator.validate({
            "goal": "test", "scope": "s", "risk": "low", "audit_log": True,
        })
        self.assertIn("valid", result)
        self.assertIn("errors", result)
        self.assertIn("warnings", result)
        self.assertIn("error_count", result)
        self.assertIn("warning_count", result)
        self.assertIn("timestamp", result)


# ======================================================================
# RuntimePolicy Tests
# ======================================================================

class TestRuntimePolicy(unittest.TestCase):
    """Test runtime policy enforcement pipeline."""

    @classmethod
    def setUpClass(cls):
        from aios_core.storage import Database
        cls.db = Database(":memory:")
        cls.runtime = RuntimePolicy(
            CONSTITUTION_DIR, POLICIES_DIR, db=cls.db
        )

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_simple_allow(self):
        result = self.runtime.request_execution({
            "goal": "Read metrics",
            "scope": "monitoring",
            "risk": "low",
            "audit_log": True,
            "agent_id": "monitor-agent-01",
            "authority": "reader",
        })
        self.assertTrue(result["allowed"])
        self.assertEqual(result["decision"], "ALLOW")

    def test_deny_creates_no_approval(self):
        result = self.runtime.request_execution({
            "goal": "test",
            "scope": "s",
            "risk": "low",
        })
        self.assertFalse(result["allowed"])
        self.assertIsNone(result["approval_id"])

    def test_review_creates_approval(self):
        result = self.runtime.request_execution({
            "goal": "Deploy module",
            "scope": "production",
            "risk": "high",
            "audit_log": True,
            "authority": "operator",
        })
        self.assertFalse(result["allowed"])
        self.assertEqual(result["decision"], "REVIEW")
        self.assertIsNotNone(result["approval_id"])

    def test_approve_review_action(self):
        result = self.runtime.request_execution({
            "goal": "Risk action",
            "scope": "production",
            "risk": "high",
            "audit_log": True,
            "authority": "operator",
        })
        approval_id = result["approval_id"]
        if approval_id is not None:
            approved = self.runtime.approve(approval_id)
            self.assertIsNotNone(approved)
            self.assertEqual(approved["status"], "approved")

    def test_deny_review_action(self):
        result = self.runtime.request_execution({
            "goal": "Another risk",
            "scope": "production",
            "risk": "high",
            "audit_log": True,
            "authority": "operator",
        })
        approval_id = result["approval_id"]
        if approval_id is not None:
            denied = self.runtime.deny(approval_id)
            self.assertIsNotNone(denied)
            self.assertEqual(denied["status"], "denied")

    def test_result_has_validation(self):
        result = self.runtime.request_execution({
            "goal": "test", "scope": "s", "risk": "low", "audit_log": True,
        })
        self.assertIn("validation", result)
        self.assertIn("valid", result["validation"])

    def test_result_has_evaluation(self):
        result = self.runtime.request_execution({
            "goal": "test", "scope": "s", "risk": "low", "audit_log": True,
        })
        self.assertIn("evaluation_id", result)
        self.assertIn("matched_articles", result)

    def test_history(self):
        history = self.runtime.history()
        self.assertGreater(len(history), 0)

    def test_stats(self):
        stats = self.runtime.stats()
        self.assertEqual(stats["version"], "9.0.0-alpha.13")
        self.assertGreater(stats["total_executions"], 0)
        self.assertIn("outcomes", stats)

    def test_audit_logging(self):
        """Verify audit events are recorded."""
        events = self.runtime.audit.query("execution_decision")
        self.assertGreater(len(events), 0)
        event = events[-1]
        self.assertIn("decision", event)
        self.assertIn("timestamp", event)

    def test_restricted_action_review_pipeline(self):
        """Restricted action should go through full REVIEW pipeline."""
        result = self.runtime.request_execution({
            "goal": "Modify core",
            "scope": "core",
            "risk": "high",
            "audit_log": True,
            "action_type": "direct_core_modification",
        })
        self.assertEqual(result["decision"], "REVIEW")
        self.assertIsNotNone(result["approval_id"])


if __name__ == "__main__":
    unittest.main()