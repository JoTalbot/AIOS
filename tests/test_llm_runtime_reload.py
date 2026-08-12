from __future__ import annotations

import json
import os
import time

from aios_core.llm_balancer import APIKey, LLMBalancer, Provider
from tg_bot import llm as telegram_llm


def _write_runtime(path, *, url: str, key: str) -> None:
    path.write_text(
        json.dumps(
            {
                "colab_llm": {
                    "enabled": True,
                    "base_url": url,
                    "api_key": key,
                    "model": "colab/qwen2.5-coder",
                }
            }
        ),
        encoding="utf-8",
    )
    os.utime(path, None)


def test_colab_runtime_hot_reload_preserves_other_provider_cooldowns(tmp_path, monkeypatch):
    runtime = tmp_path / ".llm_keys.json"
    _write_runtime(runtime, url="https://first.test/v1", key="first-key")
    monkeypatch.setattr(LLMBalancer, "_runtime_key_paths", staticmethod(lambda: (runtime,)))
    monkeypatch.setenv("LOCAL_LLM", "0")
    monkeypatch.setenv("AIOS_COLAB_MODE", "active")

    balancer = LLMBalancer()
    groq_key = APIKey(key="groq-key", provider="groq", cooldown_until=time.time() + 600)
    groq = Provider(name="groq", base_url="https://groq.test", keys=[groq_key], models=["m"])
    balancer.providers["groq"] = groq
    first_colab = balancer.providers["colab"]

    time.sleep(0.002)
    _write_runtime(runtime, url="https://second.test/v1", key="second-key")
    assert balancer.refresh_runtime_config() is True

    assert balancer.providers["groq"] is groq
    assert balancer.providers["groq"].keys[0].cooldown_until == groq_key.cooldown_until
    assert balancer.providers["colab"] is not first_colab
    assert balancer.providers["colab"].base_url == "https://second.test/v1/chat/completions"
    assert balancer.providers["colab"].keys[0].key == "second-key"


def test_unchanged_runtime_keeps_colab_circuit_state(tmp_path, monkeypatch):
    runtime = tmp_path / ".llm_keys.json"
    _write_runtime(runtime, url="https://same.test/v1", key="same-key")
    monkeypatch.setattr(LLMBalancer, "_runtime_key_paths", staticmethod(lambda: (runtime,)))
    monkeypatch.setenv("LOCAL_LLM", "0")
    monkeypatch.setenv("AIOS_COLAB_MODE", "active")
    balancer = LLMBalancer()
    provider = balancer.providers["colab"]
    provider.keys[0].cooldown_until = time.time() + 60

    assert balancer.refresh_runtime_config() is False
    assert balancer.providers["colab"] is provider
    assert not provider.keys[0].is_available


def test_telegram_uses_one_shared_balancer(monkeypatch):
    monkeypatch.setenv("LOCAL_LLM", "0")
    monkeypatch.setenv("AIOS_COLAB_MODE", "active")
    monkeypatch.setattr(telegram_llm, "_balancer_instance", None)
    first = telegram_llm._get_shared_balancer()
    second = telegram_llm._get_shared_balancer()
    assert first is second


def test_last_route_metadata_is_copied():
    telegram_llm._set_last_llm_metadata(provider="colab", model="colab/qwen2.5-coder")
    value = telegram_llm.get_last_llm_metadata()
    value["provider"] = "changed"
    assert telegram_llm.get_last_llm_metadata()["provider"] == "colab"


def test_multinode_colab_fails_over_before_cloud(monkeypatch):
    import requests

    monkeypatch.setenv("LLM_CACHE", "0")
    config = {
        "base_url": "https://primary.test/v1",
        "api_key": "primary-key",
        "model": "colab/qwen2.5-coder",
        "node_id": "primary",
        "_nodes": [
            {
                "base_url": "https://standby.test/v1",
                "api_key": "standby-key",
                "model": "colab/qwen2.5-coder",
                "node_id": "standby-1",
            }
        ],
    }
    provider = LLMBalancer._build_colab_provider(config)
    balancer = LLMBalancer()
    balancer.providers = {"colab": provider}
    monkeypatch.setattr(balancer, "refresh_runtime_config", lambda **_kwargs: False)
    balancer.task_priority["chat"] = ["colab"]
    called: list[str] = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "from standby"}}]}

    def post(url, **_kwargs):
        called.append(url)
        if "primary.test" in url:
            raise requests.ConnectionError("primary unavailable")
        return Response()

    monkeypatch.setattr(requests, "post", post)
    answer = balancer.chat(
        [{"role": "user", "content": "hello"}],
        model="llama-3.1-8b-instant",
        task_type="chat",
    )

    assert answer == "from standby"
    assert called == [
        "https://primary.test/v1/chat/completions",
        "https://standby.test/v1/chat/completions",
    ]
    assert balancer.last_route["node_id"] == "standby-1"
    assert balancer.last_route["provider"] == "colab"


def test_route_metadata_is_thread_local():
    import threading

    balancer = LLMBalancer()
    barrier = threading.Barrier(2)
    values: dict[str, dict] = {}

    def worker(name: str) -> None:
        balancer.last_route = {"provider": name, "model": name + "-model"}
        barrier.wait(timeout=2)
        values[name] = balancer.last_route

    first = threading.Thread(target=worker, args=("colab",))
    second = threading.Thread(target=worker, args=("groq",))
    first.start()
    second.start()
    first.join(timeout=2)
    second.join(timeout=2)

    assert values["colab"]["provider"] == "colab"
    assert values["groq"]["provider"] == "groq"
