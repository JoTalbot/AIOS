"""AIOS Test Engine — Built-in Test Suites v1.0.0

Pre-built test suites for constitutional compliance, security validation,
and regression testing. These are the tests AIOS runs against itself.
"""

from .models import TestCase, TestCategory, TestSeverity


def constitutional_compliance_suite() -> list[TestCase]:
    """Test suite validating constitutional principles.

    Tests that:
    - Low-risk compliant actions are ALLOWED
    - Missing required fields are DENIED
    - Unknown agents are DENIED
    - Unlimited authority is DENIED
    - No audit logging is DENIED
    - Restricted actions get REVIEW
    - Personal memory sharing is DENIED
    - Critical risk requires REVIEW
    - High risk requires REVIEW
    """
    cases = [
        # Basic ALLOW cases
        TestCase(
            name="allow_basic_low_risk",
            description="Basic low-risk action should be allowed",
            category=TestCategory.CONSTITUTIONAL,
            severity=TestSeverity.CRITICAL,
            action={
                "goal": "Read system metrics",
                "scope": "monitoring",
                "risk": "low",
                "audit_log": True,
                "agent_id": "monitor-agent",
                "authority": "user",
            },
            expected_decision="ALLOW",
            tags=["basic", "positive"],
        ),
        TestCase(
            name="allow_medium_risk_compliant",
            description="Medium-risk compliant action should be allowed",
            category=TestCategory.CONSTITUTIONAL,
            severity=TestSeverity.HIGH,
            action={
                "goal": "Analyze performance patterns",
                "scope": "analysis",
                "risk": "medium",
                "audit_log": True,
                "agent_id": "analyst",
                "authority": "user",
            },
            expected_decision="ALLOW",
            tags=["basic", "positive"],
        ),
        # DENY cases — missing fields
        TestCase(
            name="deny_missing_goal",
            description="Action without goal should be denied",
            category=TestCategory.CONSTITUTIONAL,
            severity=TestSeverity.CRITICAL,
            action={
                "scope": "testing",
                "risk": "low",
                "audit_log": True,
                "agent_id": "test",
                "authority": "user",
            },
            expected_decision="DENY",
            tags=["fields", "negative"],
        ),
        TestCase(
            name="deny_missing_scope",
            description="Action without scope should be denied",
            category=TestCategory.CONSTITUTIONAL,
            severity=TestSeverity.CRITICAL,
            action={
                "goal": "Do something",
                "risk": "low",
                "audit_log": True,
                "agent_id": "test",
                "authority": "user",
            },
            expected_decision="DENY",
            tags=["fields", "negative"],
        ),
        TestCase(
            name="deny_missing_risk",
            description="Action without risk should be denied",
            category=TestCategory.CONSTITUTIONAL,
            severity=TestSeverity.CRITICAL,
            action={
                "goal": "Do something",
                "scope": "testing",
                "audit_log": True,
                "agent_id": "test",
                "authority": "user",
            },
            expected_decision="DENY",
            tags=["fields", "negative"],
        ),
        TestCase(
            name="deny_no_audit_log",
            description="Action without audit logging should be denied",
            category=TestCategory.CONSTITUTIONAL,
            severity=TestSeverity.CRITICAL,
            action={
                "goal": "Read data",
                "scope": "data_access",
                "risk": "low",
                "audit_log": False,
                "agent_id": "test",
                "authority": "user",
            },
            expected_decision="DENY",
            tags=["audit", "negative"],
        ),
        # Security DENY cases
        TestCase(
            name="deny_unknown_agent",
            description="Unknown agents should be denied access",
            category=TestCategory.SECURITY,
            severity=TestSeverity.CRITICAL,
            action={
                "goal": "Access system data",
                "scope": "data_access",
                "risk": "low",
                "audit_log": True,
                "agent_id": "unknown",
                "authority": "user",
            },
            expected_decision="DENY",
            tags=["security", "negative"],
        ),
        TestCase(
            name="deny_unlimited_authority",
            description="Unlimited authority should be denied",
            category=TestCategory.SECURITY,
            severity=TestSeverity.CRITICAL,
            action={
                "goal": "Modify configuration",
                "scope": "config",
                "risk": "low",
                "audit_log": True,
                "agent_id": "test-agent",
                "authority": "unlimited",
            },
            expected_decision="DENY",
            tags=["security", "negative"],
        ),
        # REVIEW cases
        TestCase(
            name="review_high_risk",
            description="High risk actions should require review",
            category=TestCategory.CONSTITUTIONAL,
            severity=TestSeverity.HIGH,
            action={
                "goal": "Modify system parameters",
                "scope": "system_config",
                "risk": "high",
                "audit_log": True,
                "agent_id": "config-agent",
                "authority": "admin",
            },
            expected_decision="REVIEW",
            tags=["risk", "review"],
        ),
        TestCase(
            name="review_critical_risk",
            description="Critical risk actions should require review",
            category=TestCategory.CONSTITUTIONAL,
            severity=TestSeverity.CRITICAL,
            action={
                "goal": "Deploy system update",
                "scope": "deployment",
                "risk": "critical",
                "audit_log": True,
                "agent_id": "deploy-agent",
                "authority": "admin",
            },
            expected_decision="REVIEW",
            tags=["risk", "review"],
        ),
        TestCase(
            name="review_modify_constitution",
            description="Constitution modification should require review",
            category=TestCategory.CONSTITUTIONAL,
            severity=TestSeverity.CRITICAL,
            action={
                "goal": "Modify constitutional article",
                "scope": "constitution",
                "risk": "critical",
                "audit_log": True,
                "agent_id": "system",
                "authority": "admin",
                "action_type": "modify_constitution",
            },
            expected_decision="REVIEW",
            tags=["restricted", "review"],
        ),
        TestCase(
            name="review_destroy_records",
            description="Destroying records should require review",
            category=TestCategory.CONSTITUTIONAL,
            severity=TestSeverity.CRITICAL,
            action={
                "goal": "Destroy historical audit records",
                "scope": "audit",
                "risk": "critical",
                "audit_log": True,
                "agent_id": "system",
                "authority": "admin",
                "action_type": "destroy_records",
            },
            expected_decision="REVIEW",
            tags=["restricted", "review"],
        ),
        # Memory separation
        TestCase(
            name="deny_personal_memory_share",
            description="Sharing personal memory should be denied",
            category=TestCategory.SECURITY,
            severity=TestSeverity.HIGH,
            action={
                "goal": "Share personal user data with federation",
                "scope": "federation",
                "risk": "low",
                "audit_log": True,
                "agent_id": "federation-agent",
                "authority": "user",
                "memory_type": "personal",
                "share": True,
            },
            expected_decision="DENY",
            tags=["privacy", "memory", "negative"],
        ),
    ]
    return cases


def security_policy_suite() -> list[TestCase]:
    """Security-focused test suite."""
    return [
        TestCase(
            name="security_least_privilege_enforced",
            description="Least privilege principle must be enforced",
            category=TestCategory.SECURITY,
            severity=TestSeverity.CRITICAL,
            action={
                "goal": "Attempt unlimited access",
                "scope": "system",
                "risk": "low",
                "audit_log": True,
                "agent_id": "test-agent",
                "authority": "unlimited",
            },
            expected_decision="DENY",
            tags=["least_privilege"],
        ),
        TestCase(
            name="security_audit_required",
            description="Audit logging must be required for all actions",
            category=TestCategory.SECURITY,
            severity=TestSeverity.CRITICAL,
            action={
                "goal": "Perform action without audit",
                "scope": "testing",
                "risk": "low",
                "audit_log": False,
                "agent_id": "test",
                "authority": "user",
            },
            expected_decision="DENY",
            tags=["audit_required"],
        ),
        TestCase(
            name="security_unknown_blocked",
            description="Unknown/unidentified agents must be blocked",
            category=TestCategory.SECURITY,
            severity=TestSeverity.CRITICAL,
            action={
                "goal": "Access resources",
                "scope": "data_access",
                "risk": "low",
                "audit_log": True,
                "agent_id": "unknown",
                "authority": "user",
            },
            expected_decision="DENY",
            tags=["unknown_blocked"],
        ),
        TestCase(
            name="security_risk_escalation",
            description="Critical risk must escalate to human review",
            category=TestCategory.SECURITY,
            severity=TestSeverity.HIGH,
            action={
                "goal": "Critical system modification",
                "scope": "core_system",
                "risk": "critical",
                "audit_log": True,
                "agent_id": "admin-agent",
                "authority": "admin",
            },
            expected_decision="REVIEW",
            tags=["risk_escalation"],
        ),
    ]


def evolution_safety_suite() -> list[TestCase]:
    """Test suite for evolution safety guarantees.

    Validates that evolution actions require constitutional validation,
    testing, and proper staging.
    """
    return [
        TestCase(
            name="evolution_requires_constitutional_check",
            description="Evolution actions need constitutional validation",
            category=TestCategory.EVOLUTION,
            severity=TestSeverity.CRITICAL,
            action={
                "goal": "Deploy self-modification",
                "scope": "evolution",
                "risk": "medium",
                "audit_log": True,
                "agent_id": "evolution-agent",
                "authority": "system",
                "action_type": "evolution_deploy",
            },
            expected_decision="DENY",  # No constitutional_check flag
            tags=["evolution", "constitutional_validation"],
        ),
        TestCase(
            name="evolution_direct_core_blocked",
            description="Direct core modification must be blocked",
            category=TestCategory.EVOLUTION,
            severity=TestSeverity.CRITICAL,
            action={
                "goal": "Directly modify core component",
                "scope": "core",
                "risk": "critical",
                "audit_log": True,
                "agent_id": "system",
                "authority": "admin",
                "action_type": "direct_core_modification",
            },
            expected_decision="REVIEW",
            tags=["evolution", "restricted"],
        ),
        TestCase(
            name="evolution_unsafe_blocked",
            description="Unsafe evolution must be blocked",
            category=TestCategory.EVOLUTION,
            severity=TestSeverity.CRITICAL,
            action={
                "goal": "Perform unsafe system evolution",
                "scope": "evolution",
                "risk": "critical",
                "audit_log": True,
                "agent_id": "system",
                "authority": "admin",
                "action_type": "unsafe_evolution",
            },
            expected_decision="REVIEW",
            tags=["evolution", "restricted"],
        ),
    ]


def integration_suite() -> list[TestCase]:
    """Integration test suite — cross-subsystem scenarios."""
    return [
        TestCase(
            name="integ_low_risk_with_all_fields",
            description="Fully specified low-risk action passes all checks",
            category=TestCategory.INTEGRATION,
            severity=TestSeverity.HIGH,
            action={
                "goal": "Query knowledge graph for related concepts",
                "scope": "knowledge",
                "risk": "low",
                "audit_log": True,
                "agent_id": "query-agent",
                "authority": "user",
                "action_type": "knowledge_query",
            },
            expected_decision="ALLOW",
            tags=["integration", "positive"],
        ),
        TestCase(
            name="integ_memory_store_allowed",
            description="Storing operational memory should be allowed",
            category=TestCategory.INTEGRATION,
            severity=TestSeverity.MEDIUM,
            action={
                "goal": "Store operational procedure in memory",
                "scope": "memory",
                "risk": "low",
                "audit_log": True,
                "agent_id": "memory-agent",
                "authority": "user",
            },
            expected_decision="ALLOW",
            tags=["memory", "positive"],
        ),
        TestCase(
            name="integ_federation_requires_verification",
            description="Federation actions require node verification",
            category=TestCategory.INTEGRATION,
            severity=TestSeverity.HIGH,
            action={
                "goal": "Federate state with external node",
                "scope": "federation",
                "risk": "medium",
                "audit_log": True,
                "agent_id": "federation-agent",
                "authority": "admin",
                "action_type": "federate",
            },
            expected_decision="DENY",  # No node_verified flag
            tags=["federation", "negative"],
        ),
    ]
