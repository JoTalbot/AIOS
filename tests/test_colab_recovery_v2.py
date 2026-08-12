from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import colab_automation_runner as runner
from scripts import register_colab_llm as register


class _Response:
    status = 200

    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()


def test_probe_registered_endpoint_requires_configured_model(monkeypatch):
    monkeypatch.setattr(
        runner.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: _Response({"data": [{"id": runner.COLAB_MODEL}]}),
    )
    assert runner._probe_colab_config(
        {"base_url": "https://unit.test/v1", "api_key": "secret", "model": runner.COLAB_MODEL}
    )
    assert not runner._probe_colab_config(
        {"base_url": "https://unit.test/v1", "api_key": "secret", "model": "missing"}
    )


def test_fresh_tunnel_rejects_stale_output():
    old = {"https://old.trycloudflare.com/v1"}
    assert runner._select_fresh_tunnel(list(old), old, False) == ""
    assert runner._select_fresh_tunnel(
        ["https://old.trycloudflare.com/v1", "https://new.trycloudflare.com/v1"], old, False
    ) == "https://new.trycloudflare.com/v1"
    assert runner._select_fresh_tunnel(list(old), old, True) == "https://old.trycloudflare.com/v1"


def test_rotation_updates_only_secret_files(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    keeper_file = tmp_path / ".colab_llm.env"
    env_file.write_text("OTHER=value\nCOLAB_LLM_API_KEY=old\n", encoding="utf-8")
    monkeypatch.setattr(runner, "COLAB_ENV_FILE", env_file)
    monkeypatch.setattr(runner, "COLAB_KEEPER_ENV_FILE", keeper_file)
    monkeypatch.setenv("COLAB_LLM_API_KEY", "old")
    monkeypatch.setenv("COLAB_ROTATE_KEY_ON_RECOVERY", "1")

    new_key = runner._rotate_colab_api_key()

    assert new_key != "old"
    assert "OTHER=value" in env_file.read_text(encoding="utf-8")
    assert f"COLAB_LLM_API_KEY={new_key}" in env_file.read_text(encoding="utf-8")
    assert keeper_file.read_text(encoding="utf-8") == f"COLAB_LLM_API_KEY={new_key}\n"
    assert keeper_file.stat().st_mode & 0o777 == 0o600


def test_verify_requires_consecutive_successes(monkeypatch):
    calls = []

    def fake_request(url, _key, **_kwargs):
        calls.append(url)
        if url.endswith("/models"):
            return {"data": [{"id": register.COLAB_MODEL if hasattr(register, "COLAB_MODEL") else "colab/qwen2.5-coder"}]}
        return {"choices": [{"message": {"content": "ok"}}]}

    monkeypatch.setattr(register, "_request_json", fake_request)
    result = register.verify_colab_endpoint(
        "https://unit.test/v1",
        "secret",
        attempts=3,
        interval=0,
        required_successes=2,
    )
    assert result["ok"] is True
    assert result["attempts"] == 2
    assert len(calls) == 4


def test_registration_is_atomic_and_preserves_other_keys(tmp_path, monkeypatch):
    keys_file = tmp_path / ".llm_keys.json"
    env_file = tmp_path / ".env"
    keys_file.write_text(json.dumps({"groq": ["keep"]}), encoding="utf-8")
    env_file.write_text("OTHER=value\n", encoding="utf-8")
    monkeypatch.setattr(register, "KEYS_FILE", keys_file)
    monkeypatch.setattr(register, "ENV_FILE", env_file)

    config = register.register_colab_endpoint(
        "https://unit.test",
        api_key="secret",
        verify=False,
    )

    saved = json.loads(keys_file.read_text(encoding="utf-8"))
    assert saved["groq"] == ["keep"]
    assert config["base_url"] == "https://unit.test/v1"
    assert saved["colab_llm"]["api_key"] == "secret"
    assert "OTHER=value" in env_file.read_text(encoding="utf-8")
    assert keys_file.stat().st_mode & 0o777 == 0o600


def test_verify_fails_closed(monkeypatch):
    monkeypatch.setattr(
        register,
        "_request_json",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("down")),
    )
    with pytest.raises(RuntimeError, match="did not become stable"):
        register.verify_colab_endpoint(
            "https://unit.test/v1",
            "secret",
            attempts=2,
            interval=0,
        )


def test_standby_registration_preserves_primary_publication(tmp_path, monkeypatch):
    keys_file = tmp_path / ".llm_keys.json"
    env_file = tmp_path / ".env"
    monkeypatch.setattr(register, "KEYS_FILE", keys_file)
    monkeypatch.setattr(register, "ENV_FILE", env_file)

    register.register_colab_endpoint(
        "https://primary.test/v1",
        api_key="primary-secret",
        verify=False,
        node_id="primary",
        publish_primary=True,
    )
    register.register_colab_endpoint(
        "https://standby.test/v1",
        api_key="standby-secret",
        verify=False,
        node_id="standby-1",
        publish_primary=False,
    )

    saved = json.loads(keys_file.read_text(encoding="utf-8"))
    assert saved["colab_llm"]["node_id"] == "primary"
    assert {item["node_id"] for item in saved["colab_llm_nodes"]} == {
        "primary",
        "standby-1",
    }
    env = env_file.read_text(encoding="utf-8")
    assert "COLAB_LLM_URL=https://primary.test/v1" in env
    assert "standby.test" not in env


def test_tunnel_provider_auto_prefers_tailscale_when_configured(monkeypatch):
    monkeypatch.setenv("COLAB_TUNNEL_PROVIDER", "auto")
    monkeypatch.delenv("TAILSCALE_AUTH_KEY", raising=False)
    monkeypatch.delenv("COLAB_LLM_PUBLIC_URL", raising=False)
    assert runner._configured_tunnel_provider() == "quick"

    monkeypatch.setenv("TAILSCALE_AUTH_KEY", "runtime-secret")
    monkeypatch.setenv("COLAB_LLM_PUBLIC_URL", "https://node.tail.example")
    assert runner._configured_tunnel_provider() == "tailscale"


def test_endpoint_extraction_accepts_provider_neutral_marker():
    output = "ready\nCOLAB_LLM_URL=https://node.tail.example/v1\n"
    assert runner._extract_endpoint_urls(output) == ["https://node.tail.example/v1"]


def test_waiter_requires_current_tunnel_generation_for_stable_url(monkeypatch):
    import asyncio

    stable = "https://node.tail.example/v1"

    async def no_sleep(_seconds):
        return None

    async def stale_output(_page):
        return (
            f"COLAB_LLM_URL={stable}\n"
            "COLAB_TUNNEL_GENERATION=old-generation\n"
        )

    monkeypatch.setattr(runner.asyncio, "sleep", no_sleep)
    monkeypatch.setattr(runner, "_output_text", stale_output)
    url, fatal = asyncio.run(
        runner._wait_for_new_tunnel(
            object(),
            old_urls={stable},
            attempts=1,
            service_kind="llm",
            expected_generation="new-generation",
        )
    )
    assert url == ""
    assert fatal is False

    async def fresh_output(_page):
        return (
            f"COLAB_LLM_URL={stable}\n"
            "COLAB_TUNNEL_GENERATION=new-generation\n"
        )

    monkeypatch.setattr(runner, "_output_text", fresh_output)
    url, fatal = asyncio.run(
        runner._wait_for_new_tunnel(
            object(),
            old_urls={stable},
            attempts=1,
            service_kind="llm",
            expected_generation="new-generation",
        )
    )
    assert url == stable
    assert fatal is False


def test_runner_loads_its_own_registered_node(tmp_path, monkeypatch):
    registry = tmp_path / ".llm_keys.json"
    registry.write_text(
        json.dumps(
            {
                "colab_llm": {"node_id": "primary", "base_url": "https://primary.test/v1"},
                "colab_llm_nodes": [
                    {"node_id": "primary", "base_url": "https://primary.test/v1"},
                    {"node_id": "standby-1", "base_url": "https://standby.test/v1"},
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(runner, "COLAB_KEYS_FILE", registry)
    monkeypatch.setenv("COLAB_NODE_ID", "standby-1")
    assert runner._load_colab_runtime_config()["base_url"] == "https://standby.test/v1"


def test_first_standby_registration_does_not_publish_primary(tmp_path, monkeypatch):
    keys_file = tmp_path / ".llm_keys.json"
    env_file = tmp_path / ".env"
    monkeypatch.setattr(register, "KEYS_FILE", keys_file)
    monkeypatch.setattr(register, "ENV_FILE", env_file)

    register.register_colab_endpoint(
        "https://standby-only.test/v1",
        api_key="standby-secret",
        verify=False,
        node_id="standby-only",
        publish_primary=False,
    )
    saved = json.loads(keys_file.read_text(encoding="utf-8"))
    assert "colab_llm" not in saved
    assert saved["colab_llm_nodes"][0]["node_id"] == "standby-only"
    assert not env_file.exists()


def test_live_notebook_patch_can_be_applied_twice(monkeypatch):
    import asyncio

    scripts: list[str] = []

    class Page:
        async def evaluate(self, script, _cells):
            scripts.append(script)
            return True

    monkeypatch.setenv("COLAB_SERVICE_KIND", "llm")
    monkeypatch.setenv("COLAB_LLM_API_KEY", "unit-secret")
    monkeypatch.setenv("COLAB_TUNNEL_PROVIDER", "quick")
    first = asyncio.run(runner._prepare_llm_notebook(Page()))
    second = asyncio.run(runner._prepare_llm_notebook(Page()))

    assert first and second and first != second
    assert all("# === Быстрая подготовка" in script for script in scripts)
