"""Phase 5 — REST API Layer Tests

Tests the full AIOS REST API using httpx.AsyncClient with ASGITransport.
Covers all endpoint groups: health, stats, evaluate, tasks, memory,
knowledge graph, approvals, evolution, tests, audit, and JSON-RPC bridge.
"""

import pytest
from httpx import AsyncClient, ASGITransport

import os
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONSTITUTION_DIR = os.path.join(_PROJECT_ROOT, "docs/constitution")
POLICIES_DIR = os.path.join(_PROJECT_ROOT, "policies")


@pytest.fixture
def app():
    from aios_core.api.app import AIOSAPI
    api = AIOSAPI(
        db_path=":memory:",
        constitution_dir=CONSTITUTION_DIR,
        policies_dir=POLICIES_DIR,
        auth_required=False,
    )
    # Grant autonomy to the default development agent so tasks can execute
    api.orchestrator.autonomy.grant_autonomy("development", 4)
    return api.create_starlette_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ============================================================
# TestHealth (2 tests)
# ============================================================

class TestHealth:
    async def test_health_returns_ok(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    async def test_health_has_version(self, client):
        resp = await client.get("/health")
        data = resp.json()
        assert "version" in data
        assert data["version"] == "4.1.0-alpha"


# ============================================================
# TestStats (2 tests)
# ============================================================

class TestStats:
    async def test_stats_returns_data(self, client):
        resp = await client.get("/api/v1/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "version" in data
        assert "total_tasks" in data

    async def test_stats_has_subsystems(self, client):
        resp = await client.get("/api/v1/stats")
        data = resp.json()
        assert "subsystems" in data
        subs = data["subsystems"]
        assert "policy" in subs
        assert "memory" in subs
        assert "knowledge" in subs
        assert "evolution" in subs


# ============================================================
# TestEvaluate (3 tests)
# ============================================================

class TestEvaluate:
    async def test_evaluate_allow(self, client):
        resp = await client.post("/api/v1/evaluate", json={
            "goal": "Read system metrics",
            "scope": "monitoring",
            "risk": "low",
            "audit_log": True,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "decision" in data
        # Low risk with proper fields should get ALLOW
        assert data["decision"] == "ALLOW"

    async def test_evaluate_deny(self, client):
        resp = await client.post("/api/v1/evaluate", json={
            "goal": "Access system data",
            "scope": "data",
            "risk": "low",
            "audit_log": True,
            "agent_id": "unknown",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["decision"] == "DENY"

    async def test_evaluate_missing_fields(self, client):
        resp = await client.post("/api/v1/evaluate", json={
            "goal": "do something",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["decision"] == "DENY"
        assert "missing_required_fields" in data["reason"]


# ============================================================
# TestTasks (10 tests)
# ============================================================

class TestTasks:
    async def test_create_task(self, client):
        resp = await client.post("/api/v1/tasks", json={
            "name": "test-task",
            "description": "A test task",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "test-task"
        assert data["status"] == "pending"
        assert "task_id" in data

    async def test_create_task_with_steps(self, client):
        resp = await client.post("/api/v1/tasks", json={
            "name": "task-with-steps",
            "steps": [
                {"step_type": "tool", "params": {"x": 1}, "name": "step1"},
                {"step_type": "memory", "params": {"action": "store"}, "name": "step2"},
            ],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["steps"] == 2
        assert data["name"] == "task-with-steps"

    async def test_list_tasks(self, client):
        # Create a task first
        await client.post("/api/v1/tasks", json={"name": "for-listing"})
        resp = await client.get("/api/v1/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert "tasks" in data
        assert "count" in data
        assert data["count"] >= 1

    async def test_list_tasks_empty(self, client):
        resp = await client.get("/api/v1/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["tasks"], list)

    async def test_get_task(self, client):
        # Create a task
        create_resp = await client.post("/api/v1/tasks", json={"name": "get-me"})
        task_id = create_resp.json()["task_id"]
        # Get it
        resp = await client.get(f"/api/v1/tasks/{task_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == task_id
        assert data["name"] == "get-me"

    async def test_get_task_not_found(self, client):
        resp = await client.get("/api/v1/tasks/nonexistent_id")
        assert resp.status_code == 404
        data = resp.json()
        assert "error" in data

    async def test_execute_task(self, client):
        # Create task with a tool step (should pass evaluation with low risk)
        create_resp = await client.post("/api/v1/tasks", json={
            "name": "exec-me",
            "risk_level": "low",
            "steps": [
                {
                    "step_type": "tool",
                    "params": {"goal": "Read metrics", "scope": "monitoring", "risk": "low", "audit_log": True},
                    "name": "tool_step",
                },
            ],
        })
        task_id = create_resp.json()["task_id"]
        resp = await client.post(f"/api/v1/tasks/{task_id}/execute")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data

    async def test_execute_task_not_found(self, client):
        resp = await client.post("/api/v1/tasks/nonexistent_id/execute")
        assert resp.status_code == 404

    async def test_execute_empty_task(self, client):
        create_resp = await client.post("/api/v1/tasks", json={
            "name": "empty-task",
            "risk_level": "low",
        })
        task_id = create_resp.json()["task_id"]
        resp = await client.post(f"/api/v1/tasks/{task_id}/execute")
        assert resp.status_code == 200
        data = resp.json()
        # Empty task with no steps should complete
        assert data["status"] == "completed"
        assert data["completed_steps"] == 0

    async def test_task_lifecycle(self, client):
        # Create task with memory step
        create_resp = await client.post("/api/v1/tasks", json={
            "name": "lifecycle-task",
            "risk_level": "low",
            "steps": [
                {
                    "step_type": "memory",
                    "params": {
                        "action": "store",
                        "content": {"msg": "hello"},
                        "category": "operational",
                    },
                    "name": "store_step",
                },
            ],
        })
        task_id = create_resp.json()["task_id"]
        # Verify pending
        get_resp = await client.get(f"/api/v1/tasks/{task_id}")
        assert get_resp.json()["status"] == "pending"
        # Execute
        exec_resp = await client.post(f"/api/v1/tasks/{task_id}/execute")
        assert exec_resp.status_code == 200
        data = exec_resp.json()
        assert data["status"] == "completed"
        assert data["completed_steps"] == 1


# ============================================================
# TestMemory (10 tests)
# ============================================================

class TestMemory:
    async def test_store_memory(self, client):
        resp = await client.post("/api/v1/memory", json={
            "content": {"key": "value"},
            "category": "operational",
            "tags": ["test"],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["category"] == "operational"

    async def test_search_memory(self, client):
        # Store something first
        await client.post("/api/v1/memory", json={
            "content": {"searchable_text": "unique_marker_12345"},
            "category": "operational",
        })
        resp = await client.get("/api/v1/memory", params={
            "query": "unique_marker_12345",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert data["count"] >= 1

    async def test_get_memory(self, client):
        # Store
        store_resp = await client.post("/api/v1/memory", json={
            "content": {"x": 1},
            "category": "operational",
        })
        item_id = store_resp.json()["id"]
        # Get
        resp = await client.get(f"/api/v1/memory/{item_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == item_id
        assert data["content"]["x"] == 1

    async def test_get_memory_not_found(self, client):
        resp = await client.get("/api/v1/memory/nonexistent_id")
        assert resp.status_code == 404

    async def test_update_memory(self, client):
        store_resp = await client.post("/api/v1/memory", json={
            "content": {"old": True},
            "category": "operational",
        })
        item_id = store_resp.json()["id"]
        resp = await client.put(f"/api/v1/memory/{item_id}", json={
            "content": {"new": True},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["content"]["new"] is True

    async def test_update_memory_not_found(self, client):
        resp = await client.put("/api/v1/memory/nonexistent_id", json={
            "content": {"x": 1},
        })
        assert resp.status_code == 404

    async def test_delete_memory(self, client):
        store_resp = await client.post("/api/v1/memory", json={
            "content": {"to_delete": True},
            "category": "operational",
        })
        item_id = store_resp.json()["id"]
        resp = await client.delete(f"/api/v1/memory/{item_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted"] is True

    async def test_delete_memory_not_found(self, client):
        resp = await client.delete("/api/v1/memory/nonexistent_id")
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted"] is False

    async def test_memory_stats(self, client):
        resp = await client.get("/api/v1/memory/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "by_category" in data

    async def test_store_and_search(self, client):
        await client.post("/api/v1/memory", json={
            "content": {"type": "widget", "color": "blue"},
            "category": "operational",
            "tags": ["widget", "blue"],
        })
        await client.post("/api/v1/memory", json={
            "content": {"type": "gadget", "color": "red"},
            "category": "personal",
            "tags": ["gadget"],
        })
        # Search by category
        resp = await client.get("/api/v1/memory", params={"category": "personal"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 1
        # Search by tag
        resp2 = await client.get("/api/v1/memory", params={"tag": "widget"})
        assert resp2.status_code == 200
        assert resp2.json()["count"] >= 1


# ============================================================
# TestKnowledge (10 tests)
# ============================================================

class TestKnowledge:
    async def test_add_node(self, client):
        resp = await client.post("/api/v1/knowledge/nodes", json={
            "label": "Test Node",
            "node_type": "concept",
            "properties": {"key": "val"},
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["label"] == "Test Node"
        assert data["type"] == "concept"

    async def test_find_nodes(self, client):
        # Create a node
        await client.post("/api/v1/knowledge/nodes", json={
            "label": "Findable Node Alpha",
            "node_type": "test_type",
        })
        resp = await client.get("/api/v1/knowledge/nodes", params={
            "label": "Findable",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 1
        assert any("Findable" in n["label"] for n in data["nodes"])

    async def test_get_node(self, client):
        create_resp = await client.post("/api/v1/knowledge/nodes", json={
            "label": "Get Me Node",
        })
        node_id = create_resp.json()["id"]
        resp = await client.get(f"/api/v1/knowledge/nodes/{node_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == node_id
        assert data["label"] == "Get Me Node"

    async def test_get_node_not_found(self, client):
        resp = await client.get("/api/v1/knowledge/nodes/nonexistent_id")
        assert resp.status_code == 404

    async def test_add_edge(self, client):
        # Create two nodes
        a_resp = await client.post("/api/v1/knowledge/nodes", json={"label": "A", "node_type": "test"})
        b_resp = await client.post("/api/v1/knowledge/nodes", json={"label": "B", "node_type": "test"})
        a_id = a_resp.json()["id"]
        b_id = b_resp.json()["id"]
        # Add edge
        resp = await client.post("/api/v1/knowledge/edges", json={
            "source_id": a_id,
            "target_id": b_id,
            "relation": "connected_to",
            "weight": 0.8,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["source"] == a_id
        assert data["target"] == b_id
        assert data["relation"] == "connected_to"
        assert data["weight"] == 0.8

    async def test_get_neighbors(self, client):
        # Create nodes and edge
        a_resp = await client.post("/api/v1/knowledge/nodes", json={"label": "NbrA", "node_type": "nbr"})
        b_resp = await client.post("/api/v1/knowledge/nodes", json={"label": "NbrB", "node_type": "nbr"})
        a_id = a_resp.json()["id"]
        b_id = b_resp.json()["id"]
        await client.post("/api/v1/knowledge/edges", json={
            "source_id": a_id, "target_id": b_id, "relation": "links",
        })
        resp = await client.get(f"/api/v1/knowledge/nodes/{a_id}/neighbors")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 1
        neighbor_ids = [n["id"] for n in data["neighbors"]]
        assert b_id in neighbor_ids

    async def test_path_exists(self, client):
        # Create path: A -> B -> C
        a_resp = await client.post("/api/v1/knowledge/nodes", json={"label": "PathA", "node_type": "path"})
        b_resp = await client.post("/api/v1/knowledge/nodes", json={"label": "PathB", "node_type": "path"})
        c_resp = await client.post("/api/v1/knowledge/nodes", json={"label": "PathC", "node_type": "path"})
        a_id = a_resp.json()["id"]
        b_id = b_resp.json()["id"]
        c_id = c_resp.json()["id"]
        await client.post("/api/v1/knowledge/edges", json={
            "source_id": a_id, "target_id": b_id, "relation": "next",
        })
        await client.post("/api/v1/knowledge/edges", json={
            "source_id": b_id, "target_id": c_id, "relation": "next",
        })
        resp = await client.get("/api/v1/knowledge/path", params={
            "source": a_id, "target": c_id,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["length"] >= 1
        assert len(data["path"]) >= 1

    async def test_path_not_found(self, client):
        # Two disconnected nodes
        a_resp = await client.post("/api/v1/knowledge/nodes", json={"label": "IsoA", "node_type": "iso"})
        b_resp = await client.post("/api/v1/knowledge/nodes", json={"label": "IsoB", "node_type": "iso"})
        a_id = a_resp.json()["id"]
        b_id = b_resp.json()["id"]
        resp = await client.get("/api/v1/knowledge/path", params={
            "source": a_id, "target": b_id,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["length"] == 0
        assert data["path"] == []

    async def test_kg_stats(self, client):
        # Ensure at least one node exists
        await client.post("/api/v1/knowledge/nodes", json={"label": "Stats Node"})
        resp = await client.get("/api/v1/knowledge/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "edges" in data
        assert data["nodes"] >= 1

    async def test_kg_full_workflow(self, client):
        """Full workflow: add nodes, edges, find, traverse, stats."""
        # Add nodes
        n1 = (await client.post("/api/v1/knowledge/nodes", json={"label": "WF1", "node_type": "wf"})).json()
        n2 = (await client.post("/api/v1/knowledge/nodes", json={"label": "WF2", "node_type": "wf"})).json()
        # Add edge
        edge = (await client.post("/api/v1/knowledge/edges", json={
            "source_id": n1["id"], "target_id": n2["id"], "relation": "depends_on",
        })).json()
        assert edge["relation"] == "depends_on"
        # Find
        found = (await client.get("/api/v1/knowledge/nodes", params={"node_type": "wf"})).json()
        assert found["count"] >= 2
        # Neighbors
        nbrs = (await client.get(f"/api/v1/knowledge/nodes/{n1['id']}/neighbors")).json()
        assert nbrs["count"] >= 1
        # Stats
        stats = (await client.get("/api/v1/knowledge/stats")).json()
        assert stats["edges"] >= 1


# ============================================================
# TestApprovals (3 tests)
# ============================================================

class TestApprovals:
    async def test_list_approvals(self, client):
        resp = await client.get("/api/v1/approvals")
        assert resp.status_code == 200
        data = resp.json()
        assert "approvals" in data
        assert "count" in data
        assert isinstance(data["approvals"], list)

    async def test_approve_not_found(self, client):
        resp = await client.post("/api/v1/approvals/nonexistent_id/approve")
        assert resp.status_code == 404

    async def test_deny_not_found(self, client):
        resp = await client.post("/api/v1/approvals/nonexistent_id/deny")
        assert resp.status_code == 404


# ============================================================
# TestEvolution (10 tests)
# ============================================================

class TestEvolution:
    async def test_propose(self, client):
        resp = await client.post("/api/v1/evolution/proposals", json={
            "change": {"key": "value"},
            "component": "test_component",
            "reason": "testing",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["component"] == "test_component"
        assert data["status"] == "proposed"
        assert data["stage"] == "proposal"

    async def test_list_proposals(self, client):
        await client.post("/api/v1/evolution/proposals", json={
            "change": {}, "component": "c", "reason": "r",
        })
        resp = await client.get("/api/v1/evolution/proposals")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 1
        assert "proposals" in data

    async def test_get_proposal(self, client):
        create_resp = await client.post("/api/v1/evolution/proposals", json={
            "change": {"x": 1}, "component": "comp", "reason": "r",
        })
        proposal_id = create_resp.json()["id"]
        resp = await client.get(f"/api/v1/evolution/proposals/{proposal_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == proposal_id

    async def test_get_proposal_not_found(self, client):
        resp = await client.get("/api/v1/evolution/proposals/nonexistent_id")
        assert resp.status_code == 404

    async def test_advance_proposal(self, client):
        create_resp = await client.post("/api/v1/evolution/proposals", json={
            "change": {}, "component": "c", "reason": "r",
        })
        proposal_id = create_resp.json()["id"]
        resp = await client.post(f"/api/v1/evolution/proposals/{proposal_id}/advance")
        assert resp.status_code == 200
        data = resp.json()
        assert data["stage"] == "testing"
        assert data["stage_index"] == 1

    async def test_advance_unknown_proposal(self, client):
        resp = await client.post("/api/v1/evolution/proposals/nonexistent_id/advance")
        assert resp.status_code == 400

    async def test_approve_proposal(self, client):
        create_resp = await client.post("/api/v1/evolution/proposals", json={
            "change": {}, "component": "c", "reason": "r",
        })
        proposal_id = create_resp.json()["id"]
        # Approval is only legal after the proposal reaches the approval gate.
        for _ in range(5):
            advanced = await client.post(f"/api/v1/evolution/proposals/{proposal_id}/advance")
            assert advanced.status_code == 200
        resp = await client.post(f"/api/v1/evolution/proposals/{proposal_id}/approve")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "approved"

    async def test_reject_proposal(self, client):
        create_resp = await client.post("/api/v1/evolution/proposals", json={
            "change": {}, "component": "c", "reason": "r",
        })
        proposal_id = create_resp.json()["id"]
        resp = await client.post(
            f"/api/v1/evolution/proposals/{proposal_id}/reject",
            json={"reason": "not good enough"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "rejected"
        assert data["rejection_reason"] == "not good enough"

    async def test_deploy_check(self, client):
        create_resp = await client.post("/api/v1/evolution/proposals", json={
            "change": {}, "component": "c", "reason": "r",
        })
        proposal_id = create_resp.json()["id"]
        resp = await client.get(f"/api/v1/evolution/proposals/{proposal_id}/deploy-check")
        assert resp.status_code == 200
        data = resp.json()
        assert "can_deploy" in data
        # Fresh proposal at stage 0 should not be deployable
        assert data["can_deploy"] is False

    async def test_evolution_stats(self, client):
        resp = await client.get("/api/v1/evolution/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_proposals" in data
        assert "stages" in data
        assert len(data["stages"]) == 7


# ============================================================
# TestTests (7 tests)
# ============================================================

class TestTests:
    async def test_list_suites(self, client):
        resp = await client.get("/api/v1/tests/suites")
        assert resp.status_code == 200
        data = resp.json()
        assert "suites" in data
        assert len(data["suites"]) >= 4  # 4 built-in suites

    async def test_run_all(self, client):
        resp = await client.post("/api/v1/tests/run")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_tests" in data
        assert "total_passed" in data
        assert "overall_status" in data
        assert data["total_tests"] > 0

    async def test_run_specific_suite(self, client):
        resp = await client.post("/api/v1/tests/run/constitutional_compliance")
        assert resp.status_code == 200
        data = resp.json()
        assert data["suite_name"] == "constitutional_compliance"
        assert "total" in data
        assert "passed" in data
        assert "failed" in data
        assert data["total"] > 0

    async def test_run_unknown_suite(self, client):
        resp = await client.post("/api/v1/tests/run/nonexistent_suite")
        assert resp.status_code == 404

    async def test_last_report_not_found(self, client):
        resp = await client.get("/api/v1/tests/last-report")
        assert resp.status_code == 404

    async def test_last_report_after_run(self, client):
        # Run all tests first
        await client.post("/api/v1/tests/run")
        resp = await client.get("/api/v1/tests/last-report")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_tests" in data
        assert data["total_tests"] > 0

    async def test_test_stats(self, client):
        resp = await client.get("/api/v1/tests/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "version" in data
        assert "suites_available" in data


# ============================================================
# TestAudit (3 tests)
# ============================================================

class TestAudit:
    async def test_query_audit(self, client):
        resp = await client.get("/api/v1/audit")
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data
        assert "count" in data
        assert isinstance(data["events"], list)

    async def test_audit_stats(self, client):
        resp = await client.get("/api/v1/audit/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_events" in data
        assert "by_type" in data

    async def test_audit_with_filters(self, client):
        resp = await client.get("/api/v1/audit", params={
            "event_type": "execution_decision",
            "limit": "10",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["events"], list)


# ============================================================
# TestRPC (3 tests)
# ============================================================

class TestRPC:
    async def test_rpc_initialize(self, client):
        resp = await client.post("/rpc", json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "result" in data or "error" in data

    async def test_rpc_ping(self, client):
        resp = await client.post("/rpc", json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "ping",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("result", {}).get("pong") is True

    async def test_rpc_invalid_json(self, client):
        resp = await client.post("/rpc", content=b"not json at all")
        assert resp.status_code == 200
        data = resp.json()
        # Should get a parse error response
        assert "error" in data


# ============================================================
# TestErrorHandling (4 tests)
# ============================================================

class TestErrorHandling:
    async def test_404_for_unknown_task(self, client):
        resp = await client.get("/api/v1/tasks/this_task_does_not_exist_ever")
        assert resp.status_code == 404
        assert "error" in resp.json()

    async def test_404_for_unknown_memory(self, client):
        resp = await client.get("/api/v1/memory/no_such_memory_id_ever")
        assert resp.status_code == 404
        assert "error" in resp.json()

    async def test_400_for_missing_params_kg_path(self, client):
        resp = await client.get("/api/v1/knowledge/path")
        assert resp.status_code == 400
        assert "error" in resp.json()

    async def test_404_for_unknown_proposal(self, client):
        resp = await client.get("/api/v1/evolution/proposals/no_such_proposal")
        assert resp.status_code == 404
        assert "error" in resp.json()