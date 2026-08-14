#!/usr/bin/env python3
"""
AIOS OpenAI-compatible proxy for Kilo Code CLI.

Serves /v1/models + /v1/chat/completions on 127.0.0.1:8099.

Model selection:
  auto / llm-balancer / qwen2.5-coder  -> LLMBalancer smart routing
  <exact id from /v1/models>           -> that model via LLMBalancer
  colab/*                              -> Colab tunnel if it is actually reachable

When Kilo sends `tools`, the request is forwarded as a native OpenAI
function-calling call. Empty-content + tool_calls is a successful reply
so Kilo can actually execute bash/read/write instead of printing JSON.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

from aiohttp import web

REPO = "/root/AIOS"
sys.path.insert(0, REPO)

log = logging.getLogger("llm_proxy")

AUTO_IDS = {
    "auto",
    "llm-balancer",
    "aios-auto",
    "qwen2.5-coder",
    "colab/qwen2.5-coder",
}
COLAB_HINTS = ("colab", "qwen2.5-coder")
SELF_LOOP_MARKERS = ("127.0.0.1:8099", "localhost:8099", "[::1]:8099")

# Fast default for plain chat. Agent/tool calls need a larger-context model.
_FALLBACK_CLOUD_MODEL = "llama-3.1-8b-instant"
_FALLBACK_TOOLS_MODEL = "gemini-2.5-flash"

# Providers whose OpenAI-compat endpoints understand `tools`.
_TOOL_PROVIDERS = {
    "groq",
    "gemini",
    "openrouter",
    "mistral",
    "openai",
    "deepseek",
    "local",
    "airforce",
}
_SKIP_WHEN_TOOLS = {"cohere", "ibm"}

_OPENROUTER_MAP = {
    "gpt-3.5-turbo": "openai/gpt-3.5-turbo",
    "gpt-4o-mini": "openai/gpt-4o-mini",
    "gpt-4o": "openai/gpt-4o",
    "llama-3.1-8b-instant": "meta-llama/llama-3.1-8b-instruct",
    "llama-3.3-70b-versatile": "meta-llama/llama-3.3-70b-instruct",
    "gemini-2.5-flash": "google/gemini-2.5-flash",
    "gemini-2.5-pro": "google/gemini-2.5-pro",
}

CONTEXT_BY_PROVIDER = {
    "groq": (131072, 8192),
    "gemini": (1048576, 8192),
    "openrouter": (131072, 8192),
    "mistral": (131072, 8192),
    "cohere": (128000, 4096),
    "ibm": (131072, 4096),
    "airforce": (128000, 8192),
    "local": (32768, 4096),
    "colab": (32768, 4096),
    "openai": (128000, 16384),
    "deepseek": (128000, 8192),
}


def strip_provider_prefix(model: str) -> str:
    """Kilo may send aios/<id>. Normalize to balancer/proxy id."""
    req = (model or "").strip()
    if req.startswith("aios/"):
        req = req[5:]
    return req


def is_auto_model(model: str) -> bool:
    req = strip_provider_prefix(model)
    return (not req) or req in AUTO_IDS


def _colab_config():
    """Return (base_url, api_key, model) from .llm_keys.json + registry."""
    base_url = api_key = model = ""
    try:
        keys = json.loads(Path(REPO, "data", ".llm_keys.json").read_text())
        cfg = keys.get("colab_llm", {})
        base_url = (cfg.get("base_url") or "").strip()
        api_key = (cfg.get("api_key") or "").strip()
        model = (cfg.get("model") or "colab/qwen2.5-coder").strip()
    except Exception:
        pass
    try:
        reg = json.loads(Path(REPO, "data", ".colab_services.json").read_text())
        svc = reg.get("services", {}).get("colab-llm", {})
        reg_url = (svc.get("base_url") or "").strip()
        if reg_url and not any(marker in reg_url for marker in SELF_LOOP_MARKERS):
            if not base_url or any(marker in base_url for marker in SELF_LOOP_MARKERS):
                base_url = reg_url
        if not model:
            model = (svc.get("model") or "colab/qwen2.5-coder").strip()
    except Exception:
        pass
    if any(marker in (base_url or "") for marker in SELF_LOOP_MARKERS):
        return "", api_key, model
    return base_url, api_key, model


def _host_resolves(url: str) -> bool:
    try:
        parsed = urlparse(url)
        host = parsed.hostname
        if not host:
            return False
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        return True
    except Exception:
        return False


def colab_usable() -> bool:
    base_url, _, _ = _colab_config()
    if not base_url:
        return False
    if "trycloudflare.com" not in base_url and "tailscale" not in base_url:
        return False
    return _host_resolves(base_url)


def collect_balancer_catalog() -> list[dict]:
    catalog = [
        {
            "id": "auto",
            "name": "AIOS Auto (llm_balancer)",
            "provider": "balancer",
            "context": 131072,
            "output": 8192,
        },
        {
            "id": "qwen2.5-coder",
            "name": "Qwen2.5 Coder alias -> Auto",
            "provider": "balancer",
            "context": 32768,
            "output": 4096,
        },
    ]
    seen = {item["id"] for item in catalog}
    try:
        from aios_core.llm_balancer import LLMBalancer

        balancer = LLMBalancer()
        for prov_name, provider in balancer.providers.items():
            available = sum(1 for key in provider.keys if getattr(key, "is_available", True))
            if available <= 0:
                continue
            ctx, out = CONTEXT_BY_PROVIDER.get(prov_name, (128000, 8192))
            for model_id in provider.models:
                if not model_id or model_id in seen:
                    continue
                seen.add(model_id)
                catalog.append(
                    {
                        "id": model_id,
                        "name": f"{prov_name}: {model_id}",
                        "provider": prov_name,
                        "context": ctx,
                        "output": out,
                    }
                )
    except Exception as exc:
        log.warning("catalog from balancer failed: %s", exc)
    return catalog


def resolve_balancer_model(model: str, has_tools: bool = False) -> str:
    """Map Kilo model id to the id sent upstream."""
    req = strip_provider_prefix(model)
    if is_auto_model(req):
        return _FALLBACK_TOOLS_MODEL if has_tools else _FALLBACK_CLOUD_MODEL
    return req


def message_has_tool_calls(data: dict) -> bool:
    try:
        msg = (data.get("choices") or [{}])[0].get("message") or {}
    except Exception:
        return False
    calls = msg.get("tool_calls") or msg.get("function_call")
    return bool(calls)


def message_text(data: dict) -> str:
    try:
        content = (data.get("choices") or [{}])[0].get("message", {}).get("content")
    except Exception:
        return ""
    return content if isinstance(content, str) else ""


def completion_to_sse(data: dict, model: str) -> str:
    """Turn a non-stream OpenAI completion into SSE chunks Kilo can parse."""
    cid = data.get("id") or ("chatcmpl-aios-" + str(int(time.time() * 1000)))
    created = int(data.get("created") or time.time())
    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    finish = choice.get("finish_reason") or "stop"
    parts: list[str] = []

    def chunk(delta: dict, finish_reason=None) -> str:
        payload = {
            "id": cid,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": delta,
                    "finish_reason": finish_reason,
                }
            ],
        }
        return "data: " + json.dumps(payload, ensure_ascii=False) + "\n\n"

    role_delta: dict = {"role": "assistant"}
    if msg.get("content"):
        role_delta["content"] = ""
    parts.append(chunk(role_delta))

    content = msg.get("content")
    if isinstance(content, str) and content:
        step = 80
        parts.extend(chunk({"content": content[i : i + step]}) for i in range(0, len(content), step))

    tool_calls = msg.get("tool_calls") or []
    if not tool_calls and isinstance(msg.get("function_call"), dict):
        tool_calls = [{"id": "call_0", "type": "function", "function": msg["function_call"]}]
    if isinstance(tool_calls, list):
        for idx, call in enumerate(tool_calls):
            if not isinstance(call, dict):
                continue
            fn = call.get("function") or {}
            header = {
                "tool_calls": [
                    {
                        "index": idx,
                        "id": call.get("id") or f"call_{idx}",
                        "type": call.get("type") or "function",
                        "function": {
                            "name": fn.get("name") or "",
                            "arguments": "",
                        },
                    }
                ]
            }
            parts.append(chunk(header))
            args = fn.get("arguments") or ""
            if args:
                parts.append(
                    chunk(
                        {
                            "tool_calls": [
                                {
                                    "index": idx,
                                    "function": {"arguments": args},
                                }
                            ]
                        }
                    )
                )

    parts.append(chunk({}, finish_reason=finish))
    parts.append("data: [DONE]\n\n")
    return "".join(parts)


def _map_model_for_provider(prov_name: str, try_model: str, provider) -> str | None:
    if prov_name == "colab":
        keys = getattr(provider, "keys", []) or []
        return (keys[0].model if keys and getattr(keys[0], "model", "") else None) or (
            provider.models[0] if provider.models else try_model
        )
    if prov_name == "openrouter":
        if "/" in try_model:
            return try_model
        return _OPENROUTER_MAP.get(try_model)
    if prov_name == "local":
        inst = getattr(provider, "installed", set()) or set()
        if try_model in inst or try_model in provider.models:
            return try_model
        return provider.models[0] if provider.models else try_model
    if try_model in provider.models:
        return try_model
    if provider.models:
        return provider.models[0]
    return try_model


def iter_provider_routes(model: str, has_tools: bool):
    from aios_core.llm_balancer import LLMBalancer

    balancer = LLMBalancer()
    req = resolve_balancer_model(model, has_tools=has_tools)
    prio = list(balancer.task_priority.get("code", []))
    if has_tools:
        preferred = ["gemini", "groq", "mistral", "openrouter", "deepseek", "openai", "local"]
        prio = preferred + [name for name in prio if name not in preferred]

    seen = set()
    ordered = []
    for name in prio:
        if name in balancer.providers and name not in seen:
            ordered.append(name)
            seen.add(name)
    for name in balancer.providers:
        if name not in seen:
            ordered.append(name)
            seen.add(name)

    for name in ordered:
        if has_tools and name in _SKIP_WHEN_TOOLS:
            continue
        if has_tools and name not in _TOOL_PROVIDERS:
            continue
        provider = balancer.providers[name]
        mapped = _map_model_for_provider(name, req, provider)
        if not mapped:
            continue
        key = provider.get_next_key()
        if not key:
            continue
        yield provider, key, mapped


def openai_passthrough(body: dict) -> dict:
    """POST the OpenAI payload through a live balancer provider. Returns completion JSON."""
    import requests

    messages = body.get("messages") or []
    tools = body.get("tools") or None
    tool_choice = body.get("tool_choice")
    model = strip_provider_prefix(body.get("model") or "auto")
    has_tools = bool(tools)
    max_tokens = body.get("max_tokens") or body.get("max_completion_tokens") or 2000
    temperature = body.get("temperature", 0.3)
    last_error = "no provider"

    for provider, key, mapped in iter_provider_routes(model, has_tools):
        payload = {
            "model": mapped,
            "messages": messages,
            "max_tokens": int(max_tokens),
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = tools
            if tool_choice is not None:
                payload["tool_choice"] = tool_choice
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key.key}",
            "HTTP-Referer": "https://github.com/JoTalbot/AIOS",
            "X-Title": "AIOS Kilo Proxy",
        }
        url = key.base_url or provider.base_url
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=120)
            if resp.status_code >= 400:
                err = f"HTTP {resp.status_code} {resp.text[:160]}"
                log.warning("upstream %s/%s: %s", provider.name, mapped, err)
                provider.mark_key_error(key, err, cooldown=60 if resp.status_code >= 500 else 120)
                last_error = err
                continue
            data = resp.json()
            if not isinstance(data, dict):
                last_error = "non-json"
                continue
            if data.get("error"):
                err = str(data.get("error"))[:160]
                log.warning("upstream %s/%s error: %s", provider.name, mapped, err)
                provider.mark_key_error(key, err, cooldown=120)
                last_error = err
                continue
            if not message_text(data) and not message_has_tool_calls(data):
                log.warning("upstream %s/%s empty", provider.name, mapped)
                provider.mark_key_error(key, "empty response", cooldown=30)
                last_error = "empty"
                continue
            data.setdefault("model", model)
            log.info(
                "OK %s/%s tools=%s tool_calls=%s",
                provider.name,
                mapped,
                has_tools,
                message_has_tool_calls(data),
            )
            return data
        except Exception as exc:
            last_error = str(exc)[:160]
            log.warning("upstream %s/%s exception: %s", provider.name, mapped, last_error)
            provider.mark_key_error(key, last_error, cooldown=60)
            continue

    raise RuntimeError(last_error)


def _chat_response(text, model, prompt_tokens=0, completion_tokens=0):
    return {
        "id": "chatcmpl-aios-" + str(int(time.time() * 1000)),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


async def _proxy_colab(payload):
    """Proxy to Colab while preserving stream/tools and normalizing auto aliases."""
    if not colab_usable():
        return None
    base_url, api_key, _ = _colab_config()
    if not base_url or not api_key:
        return None
    import requests

    forwarded = dict(payload)
    if is_auto_model(str(forwarded.get("model") or "")):
        forwarded["model"] = "qwen2.5-coder"
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    stream = bool(forwarded.get("stream", False))
    try:
        resp = requests.post(url, headers=headers, json=forwarded, stream=stream, timeout=(5, 300))
        if resp.status_code >= 400:
            log.warning("Colab proxy status %s: %s", resp.status_code, resp.text[:200])
            return None
        return resp.status_code, resp.content, resp.headers.get("Content-Type", "application/json")
    except Exception as exc:
        log.warning("Colab proxy error: %s", exc)
        return None


async def handle_models(request):
    catalog = collect_balancer_catalog()
    data = [
        {
            "id": item["id"],
            "object": "model",
            "created": int(time.time()),
            "owned_by": "aios",
            "name": item["name"],
            "metadata": {
                "provider": item["provider"],
                "context": item["context"],
                "output": item["output"],
            },
        }
        for item in catalog
    ]
    return web.json_response({"object": "list", "data": data})


async def handle_chat(request):
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": {"message": "invalid json"}}, status=400)

    model = body.get("model", "auto")
    stream = bool(body.get("stream", False))
    tools = body.get("tools") or []
    req = strip_provider_prefix(model)
    log.info(
        "chat model=%s stream=%s tools=%s msgs=%s",
        req,
        stream,
        len(tools) if isinstance(tools, list) else 0,
        len(body.get("messages") or []),
    )

    if is_auto_model(req) or any(hint in req for hint in COLAB_HINTS):
        colab_resp = await _proxy_colab(body)
        if colab_resp is not None:
            status, content, ctype = colab_resp
            headers = {"Content-Type": ctype or "application/json"}
            if stream:
                headers["Content-Type"] = "text/event-stream"
            return web.Response(body=content, status=status, headers=headers)

    try:
        data = await asyncio.to_thread(openai_passthrough, body)
    except Exception as exc:
        log.error("passthrough error: %s", exc)
        return web.json_response({"error": {"message": str(exc)}}, status=502)

    if stream:
        return web.Response(text=completion_to_sse(data, req), content_type="text/event-stream")
    return web.json_response(data)


async def handle_root(request):
    return web.json_response(
        {
            "service": "aios-llm-proxy",
            "ok": True,
            "default_model": "auto",
            "colab": colab_usable(),
            "models": len(collect_balancer_catalog()),
            "tool_call": True,
        }
    )


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    port = int(os.environ.get("AIOS_PROXY_PORT", "8099"))
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_get("/v1/models", handle_models)
    app.router.add_post("/v1/chat/completions", handle_chat)
    log.info("AIOS LLM proxy listening on 127.0.0.1:%s", port)
    web.run_app(app, host="127.0.0.1", port=port, print=None)


if __name__ == "__main__":
    main()
