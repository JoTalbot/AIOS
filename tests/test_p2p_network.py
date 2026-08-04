"""Проверки облегчённого Fly.io API."""

from fastapi.testclient import TestClient

from aios_core.p2p_network import app

client = TestClient(app)


def test_root_exposes_service_links():
    response = client.get("/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "AIOS P2P Node"
    assert payload["status"] == "online"
    assert payload["docs"] == "/docs"


def test_health_is_dependency_free():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "aios-p2p"}


def test_node_discovery():
    response = client.get("/api/p2p/discover")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ACTIVE"
    assert "llm_debate" in payload["capabilities"]
    assert payload["hostname"]
    assert payload["ip"]


def test_task_endpoint_keeps_query_api_compatible():
    response = client.post("/api/p2p/task", params={"task_name": "smoke-test"})

    assert response.status_code == 200
    assert response.json()["task"] == "smoke-test"
    assert response.json()["status"] == "accepted"


def test_swarm_uses_mock_mode_without_openrouter_key(monkeypatch):
    # litellm грузит .env при первом импорте (внутри обработчика запроса),
    # что вернуло бы ключи обратно. Импортируем модуль заранее, до удаления.
    from aios_core import llm_swarm_debate  # noqa: F401
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    response = client.post("/api/swarm/debate", json={"topic": "Проверить Fly.io"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["mode"] == "mock"
    assert payload["result"]


def test_swarm_rejects_empty_topic():
    response = client.post("/api/swarm/debate", json={"topic": ""})

    assert response.status_code == 422
