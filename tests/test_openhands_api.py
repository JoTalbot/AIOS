"""Тесты F8: HTTP API контура (FastAPI TestClient, без сети и моков).

Сервис подменяется реальным ContourService на FakeClient и tmp-store.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import aios_core.openhands.api as contour_api
from aios_core.openhands import ContourService, ContourStore
from aios_core.openhands.audit import OHAuditLogger
from aios_core.orchestrator import TaskStatus
from tests.test_openhands_runner import FakeClient

TOKEN_HEADERS = {"x-octopus-token": "default"}


@pytest.fixture
def audit(tmp_path):
    from aios_core.audit_logger import AuditLogger

    return OHAuditLogger(AuditLogger(file_path=str(tmp_path / "audit.jsonl")))


@pytest.fixture
def client(tmp_path, audit, monkeypatch):
    monkeypatch.setattr(contour_api, "TOKEN", "default")
    service = ContourService(
        client=FakeClient(),
        github=None,
        audit=audit,
        store=ContourStore(state_dir=tmp_path / "state"),
    )
    contour_api.set_service(service)
    app = FastAPI()
    app.include_router(contour_api.router)
    yield TestClient(app)
    contour_api.set_service(None)


class TestAuth:
    def test_missing_token_401(self, client):
        assert client.post("/api/v1/oh-contour/tasks", json={"title": "X"}).status_code == 401

    def test_wrong_token_401(self, client):
        headers = {"x-octopus-token": "wrong"}
        assert client.post("/api/v1/oh-contour/tasks", json={"title": "X"}, headers=headers).status_code == 401

    def test_status_requires_token(self, client):
        assert client.get("/api/v1/oh-contour/tasks/any").status_code == 401


class TestSubmit:
    def test_submit_returns_task_id(self, client):
        resp = client.post("/api/v1/oh-contour/tasks", json={"title": "Фича", "description": "D"}, headers=TOKEN_HEADERS)
        assert resp.status_code == 201
        body = resp.json()
        assert body["ok"] is True
        assert body["task_id"]

    def test_submit_empty_title_422(self, client):
        resp = client.post("/api/v1/oh-contour/tasks", json={"title": ""}, headers=TOKEN_HEADERS)
        assert resp.status_code == 422

    def test_submit_unknown_gate_422(self, client):
        resp = client.post(
            "/api/v1/oh-contour/tasks",
            json={"title": "X", "required_gates": ["tests", "bogus"]},
            headers=TOKEN_HEADERS,
        )
        assert resp.status_code == 422


class TestRunAndStatus:
    def test_full_flow_via_http(self, client):
        task_id = client.post("/api/v1/oh-contour/tasks", json={"title": "Фича"}, headers=TOKEN_HEADERS).json()["task_id"]
        run = client.post(f"/api/v1/oh-contour/tasks/{task_id}/run", headers=TOKEN_HEADERS)
        assert run.status_code == 200
        result = run.json()["result"]
        assert result["status"] == TaskStatus.COMPLETED
        assert result["failure_report"] is None
        status = client.get(f"/api/v1/oh-contour/tasks/{task_id}", headers=TOKEN_HEADERS)
        assert status.status_code == 200
        assert status.json()["canonical_status"] == TaskStatus.COMPLETED
        assert set(status.json()["passed_gates"]) == {"tests", "review"}

    def test_run_unknown_task_404(self, client):
        resp = client.post("/api/v1/oh-contour/tasks/nope/run", headers=TOKEN_HEADERS)
        assert resp.status_code == 404

    def test_status_unknown_task_404(self, client):
        resp = client.get("/api/v1/oh-contour/tasks/nope", headers=TOKEN_HEADERS)
        assert resp.status_code == 404

    def test_failure_report_serialized(self, client, tmp_path, audit, monkeypatch):
        failing = FakeClient()

        def boom(cid, **kw):
            raise RuntimeError("boom")

        failing.wait_execution = boom
        service = ContourService(
            client=failing,
            github=None,
            audit=audit,
            store=ContourStore(state_dir=tmp_path / "state2"),
        )
        contour_api.set_service(service)
        task_id = client.post(
            "/api/v1/oh-contour/tasks", json={"title": "Фича", "max_retries": 1}, headers=TOKEN_HEADERS
        ).json()["task_id"]
        result = client.post(f"/api/v1/oh-contour/tasks/{task_id}/run", headers=TOKEN_HEADERS).json()["result"]
        assert result["status"] == TaskStatus.CANCELLED
        assert result["failure_report"]["attempts"] == 2  # 1 попытка + 1 retry
        assert "boom" in result["failure_report"]["last_error"]


class TestVerdict:
    def test_verdict_approved(self, client):
        task_id = client.post("/api/v1/oh-contour/tasks", json={"title": "Фича"}, headers=TOKEN_HEADERS).json()["task_id"]
        client.post(f"/api/v1/oh-contour/tasks/{task_id}/run", headers=TOKEN_HEADERS)
        resp = client.get(f"/api/v1/oh-contour/tasks/{task_id}/verdict", headers=TOKEN_HEADERS)
        assert resp.status_code == 200
        # FakeClient возвращает пустые события → fallback APPROVED, но
        # review_decision в extras не выставляется runner'ом → null.
        assert resp.json()["review_decision"] is None

    def test_verdict_unknown_task_404(self, client):
        resp = client.get("/api/v1/oh-contour/tasks/nope/verdict", headers=TOKEN_HEADERS)
        assert resp.status_code == 404


class TestProductionMount:
    """Монтирование router в прод-фабрику aios_core.api.app.create_app."""

    def test_contour_mounted_in_create_app(self, tmp_path):
        from starlette.testclient import TestClient as StarletteClient

        from aios_core.api.app import create_app
        from aios_core.openhands.service import ContourService
        from aios_core.openhands.store import ContourStore

        app = create_app(auth_required=False)
        c = StarletteClient(app)
        assert c.post("/api/v1/oh-contour/tasks", json={"title": "X"}).status_code == 401

        contour_api.set_service(ContourService(client=FakeClient(), store=ContourStore(state_dir=tmp_path)))
        try:
            resp = c.post("/api/v1/oh-contour/tasks", json={"title": "Mount"}, headers=TOKEN_HEADERS)
            assert resp.status_code == 201
            assert c.get("/health").status_code == 200  # соседние маршруты не сломаны
        finally:
            contour_api.set_service(None)

    def test_contour_disabled_by_env(self, monkeypatch):
        from starlette.testclient import TestClient as StarletteClient

        from aios_core.api.app import create_app

        monkeypatch.setenv("OH_CONTOUR_HTTP_ENABLED", "0")
        c = StarletteClient(create_app(auth_required=False))
        assert c.post("/api/v1/oh-contour/tasks", json={"title": "X"}).status_code == 404
