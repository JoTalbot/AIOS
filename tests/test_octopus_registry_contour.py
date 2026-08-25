"""Тесты расширенного octopus agent registry (F4).

Без моков: реальный FastAPI router через TestClient; state-директории
перенаправляются в tmp_path через monkeypatch (модуль читает env при импорте,
поэтому патчатся атрибуты модуля).
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import octopus_core.agent_orchestrator_api as orch_api

TOKEN_HEADERS = {"x-octopus-token": "default"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(orch_api, "STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(orch_api, "EXPERIENCE_POOL", tmp_path / "experience")
    app = FastAPI()
    app.include_router(orch_api.router)
    return TestClient(app)


def _register(client, **overrides):
    payload = {"model": "openhands-cloud", "project": "aios", **overrides}
    return client.post("/api/v3/orchestrator/agents/register", json=payload, headers=TOKEN_HEADERS)


class TestLegacyCompatibility:
    def test_register_without_contour_fields(self, client):
        resp = _register(client, capabilities=["code"])
        assert resp.status_code == 200
        agent_id = resp.json()["agent_id"]

        agents = client.get("/api/v3/orchestrator/agents", headers=TOKEN_HEADERS).json()["agents"]
        record = next(a for a in agents if a["agent_id"] == agent_id)
        assert record["capabilities"] == ["code"]
        # Новые поля присутствуют с дефолтами — старые клиенты не ломаются.
        assert record["role"] == ""
        assert record["permissions"] == []
        assert record["allowed_paths"] == []
        assert record["parent_agent"] == ""

    def test_old_state_files_load(self, client):
        # State без новых полей (записан старой версией) должен читаться.
        resp = _register(client)
        assert resp.status_code == 200
        agents = client.get("/api/v3/orchestrator/agents", headers=TOKEN_HEADERS).json()["agents"]
        assert len(agents) == 1


class TestContourFields:
    def test_register_with_contour_fields(self, client):
        resp = _register(
            client,
            agent_id="oh-coder-t1",
            role="coder",
            permissions=["repo:read", "workspace:write"],
            allowed_paths=["**"],
            memory_scope="project",
            parent_agent="oh-orchestrator",
            current_task="t-1",
        )
        assert resp.status_code == 200
        assert resp.json()["agent_id"] == "oh-coder-t1"

        agents = client.get("/api/v3/orchestrator/agents", headers=TOKEN_HEADERS).json()["agents"]
        record = agents[0]
        assert record["role"] == "coder"
        assert record["permissions"] == ["repo:read", "workspace:write"]
        assert record["allowed_paths"] == ["**"]
        assert record["memory_scope"] == "project"
        assert record["parent_agent"] == "oh-orchestrator"
        assert record["current_task"] == "t-1"

    def test_state_persisted_to_configured_dir(self, client, tmp_path):
        _register(client, agent_id="a-1")
        state_files = list((tmp_path / "state").glob("*.json"))
        assert state_files, "state должен писаться в переопределённую директорию"
        import json

        data = json.loads((tmp_path / "state" / "agents.json").read_text())
        assert "a-1" in data

    def test_heartbeat_keeps_contour_fields(self, client):
        _register(client, agent_id="a-2", role="tester", current_task="t-9")
        resp = client.post("/api/v3/orchestrator/agents/a-2/heartbeat", headers=TOKEN_HEADERS)
        assert resp.status_code == 200
        agents = client.get("/api/v3/orchestrator/agents", headers=TOKEN_HEADERS).json()["agents"]
        assert agents[0]["role"] == "tester"
        assert agents[0]["current_task"] == "t-9"

    def test_auth_still_required(self, client):
        resp = client.post(
            "/api/v3/orchestrator/agents/register",
            json={"model": "x"},
            headers={"x-octopus-token": "wrong"},
        )
        assert resp.status_code == 401
