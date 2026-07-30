"""Unit tests for AIOS v11.23.0 features: Agent Safety Guard, Autonomous Safety Audit Engine & REST/SDK Integration."""

from __future__ import annotations

from starlette.testclient import TestClient

from aios_core.ai_governance import AgentSafetyComplianceGuard, AIGovernance, AutonomousSafetyAuditEngine
from aios_core.dashboard import create_dashboard
from aios_core.orchestrator import Orchestrator
from sdk.aios_sdk import AIOSClientSync


def test_agent_safety_compliance_guard_evaluate():
    """Test real-time action safety evaluation and risk blocking."""
    guard = AgentSafetyComplianceGuard()

    # Low risk action -> allowed
    action1 = {"name": "read_public_data", "category": "query"}
    res1 = guard.evaluate_action_safety(action1)
    assert res1["allowed"] is True
    assert res1["blocked"] is False

    # High risk action with harm indicator -> blocked
    action2 = {"name": "harm_system_override", "category": "system"}
    res2 = guard.evaluate_action_safety(action2)
    assert res2["allowed"] is False
    assert res2["blocked"] is True
    assert guard.blocked_count == 1


def test_autonomous_safety_audit_engine():
    """Test multi-pillar safety audit and compliance index calculation."""
    gov = AIGovernance()
    auditor = AutonomousSafetyAuditEngine(governance=gov)

    res = auditor.run_full_safety_audit()
    assert "compliance_index" in res
    assert res["status"] in ("compliant", "degraded", "non_compliant")


def test_governance_api_endpoints_and_sdk_methods():
    """Test REST API endpoints and SDK methods for governance guard and audit."""
    orch = Orchestrator()
    app = create_dashboard(orch)
    client = TestClient(app)

    # API /api/governance/guard/evaluate
    res1 = client.post("/api/governance/guard/evaluate", json={"action": {"name": "safe_task"}})
    assert res1.status_code == 200
    assert res1.json()["allowed"] is True

    # API /api/governance/audit/run
    res2 = client.post("/api/governance/audit/run", json={"confirm": True})
    assert res2.status_code == 200
    assert "compliance_index" in res2.json()

    # API /api/governance/compliance/score
    res3 = client.get("/api/governance/compliance/score")
    assert res3.status_code == 200
    assert "compliance_index" in res3.json()

    # SDK Sync methods
    sdk = AIOSClientSync("http://localhost:8000")
    assert hasattr(sdk, "evaluate_action_safety")
    assert hasattr(sdk, "run_safety_audit")
    assert hasattr(sdk, "get_compliance_score")
