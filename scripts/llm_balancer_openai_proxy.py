#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AIOS OpenAI-compatible proxy for Kilo Code CLI.
Colab priority -> llm_balancer fallback (cloud keys -> local ollama).

Serves an OpenAI-compatible /v1/chat/completions + /v1/models endpoint on
127.0.0.1:8099. When the Colab tunnel is healthy, requests are proxied there
(preserving streaming + tool_calls). Otherwise they are routed through the
AIOS LLMBalancer (which itself prefers colab, then cloud keys, then local).
"""
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

from aiohttp import web

REPO = "/root/AIOS"
sys.path.insert(0, REPO)

log = logging.getLogger("llm_proxy")

# ---- load keys for the Colab endpoint -------------------------------
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
        if not base_url:
            base_url = (svc.get("base_url") or "").strip()
        if not model:
            model = (svc.get("model") or "colab/qwen2.5-coder").strip()
        # if registry health says degraded and we have no env override -> return empty so we skip colab
    except Exception:
        pass
    return base_url, api_key, model


def _colab_healthy():
    base_url, _, _ = _colab_config()
    if not base_url:
        return False
    if "trycloudflare.com" not in base_url and "tailscale" not in base_url:
        return False
    return True


# ---- OpenAI-compatible responses -----------------------------------
def _chat_response(text, model, prompt_tokens=0, completion_tokens=0):
    return {
        "id": "chatcmpl-aios-" + str(int(time.time() * 1000)),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": text},
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


def _sse_chunk(text, model, delta_only=False, finish=False):
    delta = {"content": text} if text else {}
    data = {
        "id": "chatcmpl-aios-" + str(int(time.time() * 1000)),
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "delta": delta,
            "finish_reason": "stop" if finish else None,
        }],
    }
    return "data: " + json.dumps(data, ensure_ascii=False) + "\n\n"


# ---- Handlers ---------------------------------------------------------
async def handle_models(request):
    models = ["qwen2.5-coder"]
    try:
        from aios_core.llm_balancer import LLMBalancer
        b = LLMBalancer()
        st = b.status()
        for name, p in st.get("providers", {}).items():
            for m in p.get("models", []):
                models.append(m)
    except Exception:
        pass
    # dedupe preserve order
    seen, out = set(), []
    for m in models:
        if m not in seen:
            seen.add(m)
            out.append(m)
    data = [{"id": m, "object": "model", "created": int(time.time()), "owned_by": "aios"} for m in out]
    return web.json_response({"object": "list", "data": data})


# Fast, reliable cloud model used when the Colab tunnel is down.
# qwen2.5-coder is NOT natively supported by any cloud provider, so asking
# the balancer for it makes it walk every dead provider then fall into the
# (OOM-prone) local 7b. We therefore default to groq's llama-3.1-8b-instant.
_FALLBACK_CLOUD_MODEL = "llama-3.1-8b-instant"


def _handle_balancer(messages, model, max_tokens, temperature):
    """Route through LLMBalancer; returns text string."""
    from aios_core.llm_balancer import LLMBalancer
    b = LLMBalancer()
    req = (model or "").strip()
    # Only request qwen2.5-coder from the balancer when the caller explicitly
    # asked for it AND a live colab/local could serve it; otherwise use the
    # fast cloud model to avoid the dead-provider walk.
    if "qwen2.5-coder" in req or "colab" in req or not req:
        req = _FALLBACK_CLOUD_MODEL
    return b.chat(messages, model=req, max_tokens=max_tokens, temperature=temperature, task_type="code")


async def _proxy_colab(payload):
    """Proxy chat completion to Colab. Returns (status, body_bytes, content_type)."""
    base_url, api_key, _ = _colab_config()
    if not base_url or not api_key:
        return None
    import requests
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    stream = payload.get("stream", False)
    try:
        resp = requests.post(url, headers=headers, json=payload, stream=stream, timeout=(10, 300))
        if resp.status_code >= 400:
            log.warning(f"Colab proxy status {resp.status_code}: {resp.text[:200]}")
            return None
        return resp.status_code, resp.content, resp.headers.get("Content-Type", "application/json")
    except Exception as e:
        log.warning(f"Colab proxy error: {e}")
        return None


async def handle_chat(request):
    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": {"message": "invalid json"}}, status=400)

    messages = body.get("messages", [])
    model = body.get("model", "qwen2.5-coder")
    stream = body.get("stream", False)
    max_tokens = body.get("max_tokens", 2000)
    temperature = body.get("temperature", 0.3)

    # 1) Try Colab first (full fidelity: streaming + tools)
    colab_resp = await _proxy_colab(body)
    if colab_resp is not None:
        status, content, ctype = colab_resp
        resp = web.Response(body=content, status=status, content_type=ctype or "application/json")
        if stream:
            resp.content_type = "text/event-stream"
        return resp

    # 2) llm_balancer fallback
    try:
        text = await asyncio.to_thread(_handle_balancer, messages, model, max_tokens, temperature)
    except Exception as e:
        log.error(f"Balancer error: {e}")
        return web.json_response({"error": {"message": str(e)}}, status=502)
    if text is None:
        text = ""
    text = str(text)

    if stream:
        words = text.split(" ")
        body_parts = []
        buf = ""
        for w in words:
            buf += (w + " ")
            if len(buf) >= 40:
                body_parts.append(_sse_chunk(buf, model))
                buf = ""
        if buf:
            body_parts.append(_sse_chunk(buf, model))
        body_parts.append(_sse_chunk("", model, finish=True))
        body_parts.append("data: [DONE]\n\n")
        return web.Response(text="".join(body_parts), content_type="text/event-stream")
    else:
        return web.json_response(_chat_response(text, model))


async def handle_root(request):
    return web.json_response({"service": "aios-llm-proxy", "ok": True, "model": "qwen2.5-coder"})


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    port = int(os.environ.get("AIOS_PROXY_PORT", "8099"))
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_get("/v1/models", handle_models)
    app.router.add_post("/v1/chat/completions", handle_chat)
    log.info(f"AIOS LLM proxy listening on 127.0.0.1:{port}")
    web.run_app(app, host="127.0.0.1", port=port, print=None)


if __name__ == "__main__":
    main()
