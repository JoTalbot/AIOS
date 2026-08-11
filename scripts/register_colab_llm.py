#!/usr/bin/env python3
"""Register a healthy private Colab OpenAI endpoint atomically.

The endpoint and API key are runtime secrets.  Logs intentionally expose only
health state and model names, never the tunnel URL or bearer token.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
KEYS_FILE = REPO_ROOT / "data" / ".llm_keys.json"
ENV_FILE = REPO_ROOT / ".env"


def _normalise_url(colab_url: str) -> str:
    value = colab_url.strip().rstrip("/")
    if not value.endswith("/v1"):
        value += "/v1"
    return value


def _request_json(url: str, api_key: str, *, payload: dict | None = None, timeout: float = 12) -> dict:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "User-Agent": "AIOS-Colab-Register/2.0",
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="GET" if body is None else "POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP {response.status}")
        return json.loads(response.read().decode("utf-8"))


def verify_colab_endpoint(
    colab_url: str,
    api_key: str,
    model_name: str = "colab/qwen2.5-coder",
    *,
    attempts: int = 8,
    interval: float = 2.0,
    required_successes: int = 2,
) -> dict:
    """Require consecutive model and completion checks before registration."""
    base_url = _normalise_url(colab_url)
    consecutive = 0
    last_error = "not checked"
    started = time.monotonic()

    for attempt in range(max(1, attempts)):
        try:
            models = _request_json(f"{base_url}/models", api_key)
            model_ids = {
                item.get("id")
                for item in models.get("data", [])
                if isinstance(item, dict)
            }
            if model_name not in model_ids:
                raise RuntimeError("configured model is absent")

            completion = _request_json(
                f"{base_url}/chat/completions",
                api_key,
                payload={
                    "model": model_name,
                    "messages": [{"role": "user", "content": "Ответь: ok"}],
                    "max_tokens": 4,
                    "temperature": 0,
                },
                timeout=30,
            )
            choices = completion.get("choices", [])
            content = choices[0].get("message", {}).get("content", "") if choices else ""
            if not str(content).strip():
                raise RuntimeError("empty completion")

            consecutive += 1
            if consecutive >= max(1, required_successes):
                return {
                    "ok": True,
                    "attempts": attempt + 1,
                    "latency_sec": round(time.monotonic() - started, 3),
                    "model": model_name,
                }
        except Exception as exc:  # endpoint failures are expected during DNS/tunnel warm-up
            consecutive = 0
            last_error = type(exc).__name__

        if attempt + 1 < attempts and interval > 0:
            time.sleep(interval)

    raise RuntimeError(
        f"Colab endpoint did not become stable after {max(1, attempts)} attempts "
        f"({last_error})"
    )


def _atomic_write(path: Path, content: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _update_env(path: Path, values: dict[str, str]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    remaining = dict(values)
    result: list[str] = []
    for line in lines:
        key = line.partition("=")[0] if "=" in line else ""
        if key in remaining:
            result.append(f"{key}={remaining.pop(key)}")
        else:
            result.append(line)
    result.extend(f"{key}={value}" for key, value in remaining.items())
    _atomic_write(path, "\n".join(result) + "\n")


def register_colab_endpoint(
    colab_url: str,
    model_name: str = "colab/qwen2.5-coder",
    *,
    api_key: str | None = None,
    verify: bool = True,
) -> dict:
    """Verify, then atomically publish one Colab endpoint generation."""
    base_url = _normalise_url(colab_url)
    secret = (api_key or os.environ.get("COLAB_LLM_API_KEY", "")).strip()
    if not secret:
        raise RuntimeError("COLAB_LLM_API_KEY is required")

    health = {"ok": True, "attempts": 0, "latency_sec": 0.0, "model": model_name}
    if verify:
        print("📡 Проверяю стабильность нового Colab LLM endpoint...")
        health = verify_colab_endpoint(base_url, secret, model_name)

    keys_data: dict = {}
    if KEYS_FILE.exists():
        try:
            keys_data = json.loads(KEYS_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            keys_data = {}

    registered_at = time.time()
    keys_data["colab_llm"] = {
        "provider": "colab",
        "base_url": base_url,
        "model": model_name,
        "api_key": secret,
        "enabled": True,
        "registered_at": registered_at,
        "health": health,
    }
    _atomic_write(KEYS_FILE, json.dumps(keys_data, indent=2, ensure_ascii=False) + "\n")
    _update_env(
        ENV_FILE,
        {
            "COLAB_LLM_URL": base_url,
            "COLAB_LLM_MODEL": model_name,
            "COLAB_LLM_API_KEY": secret,
        },
    )

    print(
        "🎉 ✅ Colab LLM зарегистрирована после "
        f"{health['attempts']} проверок; model={model_name}, latency={health['latency_sec']:.2f}s"
    )
    return keys_data["colab_llm"]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("model", nargs="?", default="colab/qwen2.5-coder")
    parser.add_argument("--no-verify", action="store_true")
    args = parser.parse_args()
    register_colab_endpoint(args.url, args.model, verify=not args.no_verify)
