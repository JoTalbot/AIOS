from scripts.llm_balancer_openai_proxy import (
    is_auto_model,
    resolve_balancer_model,
    strip_provider_prefix,
)


def test_strip_aios_prefix():
    assert strip_provider_prefix("aios/auto") == "auto"
    assert strip_provider_prefix("llama-3.1-8b-instant") == "llama-3.1-8b-instant"
    assert strip_provider_prefix("aios/google/gemini-2.0-flash-001") == "google/gemini-2.0-flash-001"


def test_auto_aliases():
    assert is_auto_model("auto")
    assert is_auto_model("aios/auto")
    assert is_auto_model("qwen2.5-coder")
    assert is_auto_model("llm-balancer")
    assert not is_auto_model("llama-3.1-8b-instant")
    assert not is_auto_model("gemini-2.5-flash")


def test_resolve_keeps_explicit_model():
    assert resolve_balancer_model("gemini-2.5-flash") == "gemini-2.5-flash"
    assert resolve_balancer_model("aios/llama-3.3-70b-versatile") == "llama-3.3-70b-versatile"
    assert resolve_balancer_model("auto") == "llama-3.1-8b-instant"
    assert resolve_balancer_model("aios/qwen2.5-coder") == "llama-3.1-8b-instant"
    assert resolve_balancer_model("auto", has_tools=True) == "gemini-2.5-flash"


def test_sse_includes_tool_calls():
    from scripts.llm_balancer_openai_proxy import completion_to_sse, message_has_tool_calls

    data = {
        "id": "chatcmpl-test",
        "created": 1,
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "bash", "arguments": '{"command":"ls"}'},
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
    }
    assert message_has_tool_calls(data)
    sse = completion_to_sse(data, "auto")
    assert "tool_calls" in sse
    assert "bash" in sse
    assert "data: [DONE]" in sse


def test_colab_proxy_normalizes_auto_and_preserves_stream(monkeypatch):
    import asyncio

    import requests

    import scripts.llm_balancer_openai_proxy as proxy

    captured = {}

    class Response:
        status_code = 200
        content = b'{"choices": []}'
        headers = {"Content-Type": "application/json; charset=utf-8"}
        text = ""

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr(proxy, "colab_usable", lambda: True)
    monkeypatch.setattr(proxy, "_colab_config", lambda: ("https://colab.example/v1", "test-key", "model"))
    monkeypatch.setattr(requests, "post", fake_post)

    result = asyncio.run(proxy._proxy_colab({"model": "aios/auto", "messages": [], "stream": True}))

    assert result == (200, Response.content, "application/json; charset=utf-8")
    assert captured["url"] == "https://colab.example/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["model"] == "qwen2.5-coder"
    assert captured["stream"] is True


def test_handle_chat_accepts_upstream_content_type_with_charset(monkeypatch):
    import asyncio

    import scripts.llm_balancer_openai_proxy as proxy

    class Request:
        async def json(self):
            return {"model": "auto", "messages": [], "stream": False}

    async def fake_colab(_payload):
        return 200, b'{"choices": []}', "application/json; charset=utf-8"

    monkeypatch.setattr(proxy, "_proxy_colab", fake_colab)
    response = asyncio.run(proxy.handle_chat(Request()))

    assert response.status == 200
    assert response.content_type == "application/json"
    assert response.charset == "utf-8"


def test_sync_kilo_config_is_atomic_and_preserves_other_providers(monkeypatch, tmp_path):
    import json
    import stat

    import scripts.sync_kilo_llm_models as sync

    path = tmp_path / "kilo.jsonc"
    path.write_text(
        json.dumps(
            {
                "model": "aios/qwen2.5-coder",
                "provider": {
                    "other": {"name": "keep"},
                    "aios": {"options": {"apiKey": "custom-key", "custom": True}},
                },
            }
        ),
        encoding="utf-8",
    )
    path.chmod(0o640)
    models = {"auto": {"id": "auto", "name": "Auto", "tool_call": True, "limit": {}}}
    monkeypatch.setattr(sync, "build_kilo_models", lambda: models)

    count, changed, default = sync.sync_kilo_config(path)
    config = json.loads(path.read_text(encoding="utf-8"))

    assert (count, changed, default) == (1, True, "aios/auto")
    assert config["provider"]["other"] == {"name": "keep"}
    assert config["provider"]["aios"]["options"] == {
        "apiKey": "custom-key",
        "custom": True,
        "baseURL": "http://127.0.0.1:8099/v1",
    }
    assert config["provider"]["aios"]["models"] == models
    assert stat.S_IMODE(path.stat().st_mode) == 0o640
    assert list(tmp_path.glob(".*.tmp")) == []
    assert sync.sync_kilo_config(path, check_only=True)[1] is False


def test_sse_normalizes_legacy_function_call():
    import scripts.llm_balancer_openai_proxy as proxy

    data = {
        "choices": [
            {
                "message": {
                    "content": None,
                    "function_call": {"name": "read_file", "arguments": '{"path":"README.md"}'},
                },
                "finish_reason": "function_call",
            }
        ]
    }

    assert proxy.message_has_tool_calls(data)
    sse = proxy.completion_to_sse(data, "auto")
    assert "tool_calls" in sse
    assert "read_file" in sse
    assert "README.md" in sse


def test_catalog_lists_only_providers_with_available_keys(monkeypatch):
    import aios_core.llm_balancer as lb
    import scripts.llm_balancer_openai_proxy as proxy

    class Key:
        def __init__(self, available):
            self.is_available = available

    class Provider:
        def __init__(self, models, available):
            self.models = models
            self.keys = [Key(available)]

    class Balancer:
        providers = {
            "groq": Provider(["model-a", "model-a"], True),
            "openai": Provider(["model-hidden"], False),
        }

    monkeypatch.setattr(lb, "LLMBalancer", Balancer)
    catalog = proxy.collect_balancer_catalog()
    ids = [item["id"] for item in catalog]

    assert ids[:2] == ["auto", "qwen2.5-coder"]
    assert ids.count("model-a") == 1
    assert "model-hidden" not in ids


def test_tool_passthrough_forwards_tools_and_accepts_empty_content(monkeypatch):
    from types import SimpleNamespace

    import requests

    import scripts.llm_balancer_openai_proxy as proxy

    marked = []
    captured = {}
    provider = SimpleNamespace(
        name="groq",
        base_url="https://provider.invalid/chat",
        mark_key_error=lambda *args, **kwargs: marked.append((args, kwargs)),
    )
    key = SimpleNamespace(key="test-key", base_url="")

    class Response:
        status_code = 200
        text = ""

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "type": "function",
                                    "function": {"name": "bash", "arguments": '{"command":"pwd"}'},
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ]
            }

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr(proxy, "iter_provider_routes", lambda *_args: iter([(provider, key, "model-tools")]))
    monkeypatch.setattr(requests, "post", fake_post)
    tools = [{"type": "function", "function": {"name": "bash", "parameters": {}}}]
    result = proxy.openai_passthrough(
        {"model": "auto", "messages": [{"role": "user", "content": "run pwd"}], "tools": tools}
    )

    assert proxy.message_has_tool_calls(result)
    assert captured["json"]["tools"] == tools
    assert captured["json"]["model"] == "model-tools"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert marked == []
