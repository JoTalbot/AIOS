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
