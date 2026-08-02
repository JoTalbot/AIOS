"""
LLM Balancer v2.1 — улучшенная балансировка с приоритетом рабочих провайдеров.

Исправления:
- 402 Payment Required = permanent dead (24h cooldown)
- Приоритет: groq > deepseek > zai > mistral > cohere > gemini > huggingface > airforce > openrouter > local
- local_first удален, local теперь всегда последний fallback
- Fallback цепочка: groq/llama, huggingface/gemma-3-27b, qwen2.5-coder:7b вместо 1.5b
- Экспоненциальный backoff для 429
- Учет installed моделей для local
"""

import json
import os
import time
import threading
from dataclasses import dataclass, field
from pathlib import Path

for _env_path in (Path(__file__).resolve().parents[1] / ".env",):
    if _env_path.exists():
        for _line in _env_path.read_text(encoding="utf-8").splitlines():
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _key, _, _value = _line.partition("=")
            _key = _key.strip()
            _value = _value.strip().strip('"').strip("'")
            if _key and _key not in os.environ:
                os.environ[_key] = _value


@dataclass
class APIKey:
    key: str
    provider: str
    last_error: str = ""
    last_used: float = 0.0
    error_count: int = 0
    cooldown_until: float = 0.0
    permanently_dead: bool = False

    @property
    def is_available(self) -> bool:
        if self.permanently_dead:
            return False
        return time.time() > self.cooldown_until


@dataclass
class Provider:
    name: str
    base_url: str
    keys: list[APIKey] = field(default_factory=list)
    models: list[str] = field(default_factory=list)
    _key_index: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)
    installed: set = field(default_factory=set)

    def get_next_key(self) -> APIKey | None:
        with self._lock:
            available = [k for k in self.keys if k.is_available]
            if not available:
                return None
            # Least recently used + lowest error count
            available_sorted = sorted(available, key=lambda k: (k.error_count, k.last_used))
            key = available_sorted[0]
            key.last_used = time.time()
            # round-robin index update
            self._key_index = (self._key_index + 1) % len(self.keys)
            return key

    def mark_key_error(self, key: APIKey, error: str, cooldown: int = 300):
        key.last_error = error
        key.error_count += 1
        # Permanent dead for 402
        if "402" in error or "Payment" in error or "insufficient" in error.lower():
            key.cooldown_until = time.time() + 86400  # 24h
            if key.error_count >= 3:
                key.permanently_dead = True
            print(f"  [Balancer] {key.provider} key marked DEAD 24h: {error} (errors={key.error_count})")
        else:
            # Exponential backoff for 429
            if "429" in error:
                cd = min(60 * (2 ** min(key.error_count, 4)), 600)
            else:
                cd = cooldown
            key.cooldown_until = time.time() + cd
            print(f"  [Balancer] {key.provider} key cooled down {cd}s: {error} (errors={key.error_count})")


class LLMBalancer:
    PROVIDERS = {
        "openrouter": {
            "base_url": "https://openrouter.ai/api/v1/chat/completions",
            "models": [
                "meta-llama/llama-4-maverick",
                "mistralai/mistral-small-3.2-24b-instruct",
                "deepseek/deepseek-chat-v3-0324",
                "openai/gpt-oss-20b:free",
                "cohere/north-mini-code:free",
                "google/gemma-4-31b-it:free",
            ],
        },
        "gemini": {
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
            "models": [
                "gemini-2.0-flash",
                "gemini-2.5-flash",
                "gemini-2.5-pro",
            ],
        },
        "openai": {
            "base_url": "https://api.openai.com/v1/chat/completions",
            "models": [
                "gpt-4o-mini",
                "gpt-4o",
                "gpt-4.1-mini",
            ],
        },
        "groq": {
            "base_url": "https://api.groq.com/openai/v1/chat/completions",
            "models": [
                "llama-3.3-70b-versatile",
                "llama-3.1-8b-instant",
                "mixtral-8x7b-32768",
                "gemma2-9b-it",
            ],
        },
        "deepseek": {
            "base_url": "https://api.deepseek.com/chat/completions",
            "models": [
                "deepseek-chat",
                "deepseek-reasoner",
                "deepseek-coder",
            ],
        },
        "zai": {
            "base_url": "https://api.z.ai/api/v1/chat/completions",
            "models": [
                "glm-4.5-flash",
                "glm-4.7-flash",
                "glm-4.5",
                "glm-5",
            ],
        },
        "cerebras": {
            "base_url": "https://api.cerebras.ai/v1/chat/completions",
            "models": [
                "llama-3.3-70b",
                "llama-3.1-8b",
            ],
        },
        "mistral": {
            "base_url": "https://api.mistral.ai/v1/chat/completions",
            "models": [
                "mistral-small-latest",
                "mistral-medium-latest",
                "open-mistral-7b",
                "codestral-latest",
            ],
        },
        "cohere": {
            "base_url": "https://api.cohere.ai/v2/chat",
            "models": [
                "command-a-03-2025",
                "command-r-08-2024",
                "command-r7b-12-2024",
            ],
        },
        "together": {
            "base_url": "https://api.together.xyz/v1/chat/completions",
            "models": [
                "meta-llama/Meta-Llama-3-70B-Instruct-Turbo",
                "mistralai/Mistral-7B-Instruct-v0.3",
                "Qwen/Qwen2.5-7B-Instruct-Turbo",
            ],
        },
        "airforce": {
            "base_url": "https://api.airforce/v1/chat/completions",
            "models": [
                "gpt-4o-mini",
                "gpt-4o",
                "claude-sonnet-4.6-rp",
                "llama-4-scout-17b-16e-instruct",
            ],
        },
        "aimlapi": {
            "base_url": "https://api.aimlapi.com/v1/chat/completions",
            "models": [
                "gpt-4o-mini",
                "gpt-4o",
                "meta-llama/Llama-3.3-70B-Instruct",
            ],
        },
        "ibm": {
            "base_url": "https://us-south.ml.cloud.ibm.com/ml/v1/chat/completions",
            "models": [
                "meta-llama/llama-3-3-70b-instruct",
            ],
        },
        "huggingface": {
            "base_url": "https://router.huggingface.co/v1/chat/completions",
            "models": [
                "meta-llama/Llama-3.3-70B-Instruct",
                "google/gemma-3-27b-it",
                "Qwen/Qwen3-30B-A3B-Instruct",
            ],
        },
        
        "github": {
            "base_url": "https://models.github.ai/inference/chat/completions",
            "models": [
                "openai/gpt-4o-mini",
                "openai/gpt-4o",
                "meta/Meta-Llama-3-70B-Instruct",
                "mistral-ai/Mistral-small",
            ],
        },
        "nvidia": {
            "base_url": "https://integrate.api.nvidia.com/v1/chat/completions",
            "models": [
                "meta/llama-3.1-8b-instruct",
                "meta/llama-3.1-70b-instruct",
                "mistralai/mistral-7b-instruct-v0.3",
                "google/gemma-2-9b-it",
            ],
        },
        "sambanova": {
            "base_url": "https://api.sambanova.ai/v1/chat/completions",
            "models": [
                "Meta-Llama-3.1-8B-Instruct",
                "Meta-Llama-3.1-70B-Instruct",
            ],
        },
        "local": {
            "base_url": os.environ.get("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1/chat/completions"),
            "models": [
                "qwen2.5-coder:7b",  # prefer 7b over 1.5b
                "qwen2.5-coder:1.5b",
                "qwen2.5-coder:14b",
                "deepseek-coder:6.7b",
            ],
        },
    }

    MODEL_FALLBACKS = {
        "openai/gpt-oss-20b:free": [
            "meta-llama/llama-4-maverick",
            "llama-3.1-8b-instant",
            "google/gemma-3-27b-it",
            "mistralai/mistral-small-3.2-24b-instruct",
        ],
        "meta-llama/llama-4-maverick": [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "gemini-2.0-flash",
            "mistralai/mistral-small-3.2-24b-instruct",
            "gpt-4o-mini",
            "deepseek-chat",
            "glm-4.5-flash",
        ],
        "gemini-2.0-flash": [
            "gemini-2.5-flash",
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "meta-llama/llama-4-maverick",
            "gpt-4o-mini",
        ],
        "gemini-2.5-flash": [
            "gemini-2.0-flash",
            "llama-3.1-8b-instant",
            "meta-llama/llama-4-maverick",
            "gpt-4o-mini",
        ],
        # gpt-4o-mini: cloud-first, local 7b last
        "gpt-4o-mini": [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "google/gemma-3-27b-it",
            "mistral-small-latest",
            "deepseek-chat",
            "glm-4.5-flash",
            "qwen2.5-coder:7b",  # local strong fallback
        ],
        "gpt-4o": [
            "gpt-4o-mini",
            "llama-3.3-70b-versatile",
            "google/gemma-3-27b-it",
            "qwen2.5-coder:7b",
        ],
        "mistralai/mistral-small-3.2-24b-instruct": [
            "llama-3.1-8b-instant",
            "meta-llama/llama-4-maverick",
            "gemini-2.0-flash",
            "gpt-4o-mini",
        ],
        "glm-4.5-flash": [
            "glm-4.7-flash",
            "deepseek-chat",
            "llama-3.1-8b-instant",
            "gemini-2.0-flash",
        ],
        "deepseek-chat": [
            "deepseek-reasoner",
            "llama-3.1-8b-instant",
            "meta-llama/llama-4-maverick",
            "gpt-4o-mini",
        ],
        "deepseek/deepseek-chat-v3-0324": [
            "deepseek-chat",
            "llama-3.1-8b-instant",
            "mistral-small-latest",
            "gpt-4o-mini",
        ],
        "llama-3.3-70b-versatile": [
            "llama-3.1-8b-instant",
            "google/gemma-3-27b-it",
            "mistral-small-latest",
        ],
        "llama-3.1-8b-instant": [
            "llama-3.3-70b-versatile",
            "mistral-small-latest",
            "google/gemma-3-27b-it",
            "gemini-2.0-flash",
        ],
        "gpt-3.5-turbo": [
            "llama-3.1-8b-instant",
            "google/gemma-3-27b-it",
            "mistralai/mistral-small-3.2-24b-instruct",
            "deepseek-chat",
        ],
        # Local -> cloud fallback
        "qwen2.5-coder:1.5b": [
            "qwen2.5-coder:7b",
            "google/gemma-3-27b-it",
            "llama-3.1-8b-instant",
            "meta-llama/llama-4-maverick",
            "gpt-4o-mini",
        ],
        "qwen2.5-coder:7b": [
            "llama-3.1-8b-instant",
            "google/gemma-3-27b-it",
            "meta-llama/Llama-3.3-70B-Instruct",
            "Qwen/Qwen3-30B-A3B-Instruct",
            "meta-llama/llama-4-maverick",
            "gpt-4o-mini",
        ],
    }

    def __init__(self):
        self.providers: dict[str, Provider] = {}
        self._load_from_env()
        self._total_requests = 0
        self._total_errors = 0
        self._provider_stats: dict[str, int] = {}
        self._cache: dict[str, str] = {}
        self._cache_max = int(os.environ.get("LLM_CACHE_MAX", "256"))
        # FIXED PRIORITY: groq и deepseek первыми (самые надежные), openrouter и local последними
                        self.task_priority = {
            "chat": ["groq", "cerebras", "github", "mistral", "cohere", "together", "nvidia", "sambanova", "gemini", "deepseek", "zai", "huggingface", "openai", "airforce", "openrouter", "aimlapi", "ibm", "local"],
            "code": ["groq", "cerebras", "github", "mistral", "cohere", "together", "nvidia", "sambanova", "huggingface", "gemini", "openai", "airforce", "openrouter", "aimlapi", "deepseek", "zai", "ibm", "local"],
            "analysis": ["groq", "cerebras", "github", "gemini", "mistral", "cohere", "together", "nvidia", "huggingface", "openai", "airforce", "openrouter", "local"],
            "general": ["groq", "cerebras", "github", "mistral", "cohere", "together", "nvidia", "sambanova", "gemini", "huggingface", "openai", "airforce", "openrouter", "aimlapi", "deepseek", "zai", "ibm", "local"],
        }

    def _load_from_env(self):
        for key_file in (Path("/app/data/.llm_keys.json"), Path(__file__).resolve().parents[1] / "data/.llm_keys.json"):
            try:
                runtime = json.loads(key_file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            env_prefix = {"openrouter": "OPENROUTER_API_KEY", "gemini": "GEMINI_API_KEY", "openai": "OPENAI_API_KEY", "deepseek": "DEEPSEEK_API_KEY", "zai": "ZAI_API_KEY", "cerebras": "CEREBRAS_API_KEY", "mistral": "MISTRAL_API_KEY", "cohere": "COHERE_API_KEY", "together": "TOGETHER_API_KEY", "huggingface": "HUGGINGFACE_API_KEY", "airforce": "AIRFORCE_API_KEY", "aimlapi": "AIMLAPI_API_KEY", "ibm": "IBM_API_KEY", "groq": "GROQ_API_KEY"}
            for provider, keys in runtime.items():
                prefix = env_prefix.get(provider)
                if not prefix or not isinstance(keys, list):
                    continue
                for index, key in enumerate(keys, 1):
                    if key and not os.environ.get(f"{prefix}_{index}"):
                        os.environ[f"{prefix}_{index}"] = str(key)

        # Generic loader helper
        def load_keys(prefix, prov_name):
            keys = []
            for i in range(1, 10):
                k = os.environ.get(f"{prefix}_{i}", "")
                if k:
                    keys.append(APIKey(key=k, provider=prov_name))
            base = os.environ.get(prefix, "")
            if base and not any(k.key == base for k in keys):
                keys.append(APIKey(key=base, provider=prov_name))
            if keys and prov_name in self.PROVIDERS:
                self.providers[prov_name] = Provider(
                    name=prov_name,
                    base_url=self.PROVIDERS[prov_name]["base_url"],
                    keys=keys,
                    models=self.PROVIDERS[prov_name]["models"],
                )

        for p, env_name in [
            ("openrouter", "OPENROUTER_API_KEY"),
            ("gemini", "GEMINI_API_KEY"),
            ("openai", "OPENAI_API_KEY"),
            ("huggingface", "HUGGINGFACE_API_KEY"),
            ("airforce", "AIRFORCE_API_KEY"),
            ("aimlapi", "AIMLAPI_API_KEY"),
            ("ibm", "IBM_API_KEY"),
            ("groq", "GROQ_API_KEY"),
            ("deepseek", "DEEPSEEK_API_KEY"),
            ("zai", "ZAI_API_KEY"),
            ("cerebras", "CEREBRAS_API_KEY"),
            ("mistral", "MISTRAL_API_KEY"),
            ("cohere", "COHERE_API_KEY"),
            ("together", "TOGETHER_API_KEY"),
            ("github", "GITHUB_API_KEY"),
            ("nvidia", "NVIDIA_API_KEY"),
            ("sambanova", "SAMBANOVA_API_KEY"),
        ]:
            load_keys(env_name, p)

        # Local Ollama
        if os.environ.get("LOCAL_LLM", "") == "1":
            try:
                import urllib.request as _ur
                with _ur.urlopen("http://localhost:11434/api/tags", timeout=2) as _r:
                    _installed = {m["name"] for m in json.loads(_r.read().decode("utf-8", "ignore")).get("models", [])}
            except Exception:
                _installed = set()
            # Filter: only keep models that are actually installed if we have info
            if _installed:
                available_models = [m for m in self.PROVIDERS["local"]["models"] if m in _installed or any(m in ins for ins in _installed)]
                if not available_models:
                    available_models = list(_installed)[:5]
            else:
                available_models = self.PROVIDERS["local"]["models"]
                _installed = set(self.PROVIDERS["local"]["models"])

            self.providers["local"] = Provider(
                name="local",
                base_url=self.PROVIDERS["local"]["base_url"],
                keys=[APIKey(key="local", provider="local")],
                models=available_models,
                installed=_installed,
            )

    def add_key(self, provider: str, key: str):
        if provider not in self.providers:
            if provider in self.PROVIDERS:
                self.providers[provider] = Provider(
                    name=provider,
                    base_url=self.PROVIDERS[provider]["base_url"],
                    models=self.PROVIDERS[provider]["models"],
                )
            else:
                print(f"  [Balancer] Unknown provider: {provider}")
                return
        self.providers[provider].keys.append(APIKey(key=key, provider=provider))

    def chat(self, messages: list[dict], model: str = "", system: str = "",
             max_tokens: int = 2000, temperature: float = 0.3,
             task_type: str = "general") -> str:
        self._total_requests += 1

        if not model:
            model = os.environ.get("LLM_MODEL", "llama-3.1-8b-instant")

        if os.environ.get("LLM_CACHE", "1") == "1":
            _key = str((system or "", [tuple(sorted(m.items())) for m in messages if isinstance(m, dict) and "role" in m and "content" in m]))
            if _key in self._cache:
                return self._cache[_key]

        models_to_try = [model] + self.MODEL_FALLBACKS.get(model, [])
        # Deduplicate
        seen = set()
        uniq_models = []
        for m in models_to_try:
            if m not in seen:
                uniq_models.append(m)
                seen.add(m)
        models_to_try = uniq_models

        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)

        for try_model in models_to_try:
            max_keys_to_try = sum(len(p.keys) for p in self.providers.values())
            keys_tried = 0

            while keys_tried < max_keys_to_try:
                # Smart provider ordering, NO local_first override
                _prio = self.task_priority.get(task_type, self.task_priority["general"])
                _providers = []
                for _n in _prio:
                    if _n in self.providers:
                        _providers.append((_n, self.providers[_n]))
                for _n, _pr in self.providers.items():
                    if _n not in _prio:
                        _providers.append((_n, _pr))

                best_provider = None
                best_key = None

                for prov_name, provider in _providers:
                    # Check model support
                    if prov_name == "openrouter":
                        model_supported = True
                    elif prov_name == "local":
                        inst = getattr(provider, "installed", set())
                        model_supported = try_model in inst or try_model in provider.models
                    else:
                        model_supported = try_model in provider.models
                        # For groq etc, also allow openrouter-style fallback models if provider is generic
                        if not model_supported and prov_name in ("groq", "deepseek", "zai", "mistral"):
                            # Allow any model if provider is known to be flexible (they will 404 if not)
                            # But we prefer to only try if model is in list or is common
                            if try_model in ("gpt-4o-mini", "gpt-4o", "llama-3.1-8b-instant", "llama-3.3-70b-versatile"):
                                model_supported = True

                    if not model_supported:
                        continue
                    k = provider.get_next_key()
                    if k:
                        best_provider = provider
                        best_key = k
                        break

                if not best_key or not best_provider:
                    break

                keys_tried += 1
                prov_name = best_provider.name

                try:
                    import requests as _req_lib
                    payload = {
                        "model": try_model,
                        "messages": all_messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    }

                    # Cohere v2 chat uses different format
                    if prov_name == "cohere":
                        # Convert to Cohere format: last user message as message, others as chat_history
                        last_msg = all_messages[-1]["content"] if all_messages else ""
                        history = [{"role": m["role"], "message": m["content"]} for m in all_messages[:-1]]
                        payload = {
                            "model": try_model,
                            "message": last_msg,
                            "chat_history": history,
                        }

                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {best_key.key}",
                        "HTTP-Referer": "https://github.com/JoTalbot/AIOS",
                        "X-Title": "AIOS Coder Orchestrator v2",
                    }

                    _resp = _req_lib.post(best_provider.base_url, json=payload, headers=headers, timeout=120)
                    _resp.raise_for_status()
                    data = _resp.json()

                    if isinstance(data, dict):
                        if data.get("success") is False or (data.get("code") and data["code"] not in (0, 200, None)):
                            err_msg = data.get("msg") or data.get("message") or str(data.get("code"))
                            print(f"  [Balancer] {prov_name} app-error: {err_msg}")
                            best_provider.mark_key_error(best_key, f"app-error: {err_msg}", cooldown=300)
                            continue
                        if "error" in data:
                            err_msg = data["error"].get("message", str(data["error"]))[:80]
                            print(f"  [Balancer] {prov_name} error: {err_msg}")
                            best_provider.mark_key_error(best_key, f"error: {err_msg}", cooldown=300)
                            continue

                    self._provider_stats[prov_name] = self._provider_stats.get(prov_name, 0) + 1
                    print(f"  [Balancer] OK: {prov_name}/{try_model}")

                    # Parse response
                    content = ""
                    if "choices" in data and data["choices"]:
                        _c = data["choices"][0].get("message", {}).get("content", "")
                        content = _c if isinstance(_c, str) else ""
                    elif "data" in data and isinstance(data["data"], dict) and "choices" in data["data"]:
                        content = data["data"]["choices"][0]["message"]["content"]
                    elif "message" in data:
                        _mc = data["message"]
                        if isinstance(_mc, dict):
                            c = _mc.get("content")
                            if isinstance(c, list):
                                content = "".join(x.get("text", "") for x in c if isinstance(x, dict))
                            else:
                                content = str(c or "")
                        else:
                            content = str(_mc)
                    elif "text" in data:  # Cohere
                        content = data.get("text", "")
                    elif "result" in data:
                        content = str(data["result"])

                    if content:
                        if os.environ.get("LLM_CACHE", "1") == "1":
                            _cache_key = str((system or "", [tuple(sorted(m.items())) for m in messages if isinstance(m, dict) and "role" in m and "content" in m]))
                            if len(self._cache) < self._cache_max:
                                self._cache[_cache_key] = content
                        return content
                    else:
                        print(f"  [Balancer] {prov_name}: empty response")
                        best_provider.mark_key_error(best_key, "empty response", cooldown=60)
                        continue

                except Exception as e:
                    _code = getattr(getattr(e, "response", None), "status_code", None) or getattr(e, "code", None)
                    if _code:
                        code = int(_code)
                        print(f"  [Balancer] {prov_name}/{try_model}: HTTP {code}")
                        if code == 402:
                            best_provider.mark_key_error(best_key, f"HTTP {code} Payment Required", cooldown=86400)
                            continue
                        elif code == 429:
                            best_provider.mark_key_error(best_key, f"HTTP {code} Rate Limited", cooldown=60)
                            continue
                        elif code == 404:
                            break
                        elif code == 401:
                            best_provider.mark_key_error(best_key, "Auth failed", cooldown=600)
                            continue
                        elif code == 403:
                            body = str(getattr(getattr(e, "response", None), "text", "") or "")[:100]
                            cd = 900 if "1010" in body else 600
                            best_provider.mark_key_error(best_key, f"HTTP {code} {body[:40]}", cooldown=cd)
                            continue
                        elif code >= 500:
                            best_provider.mark_key_error(best_key, f"HTTP {code}", cooldown=60)
                            continue
                        else:
                            best_provider.mark_key_error(best_key, f"HTTP {code}", cooldown=300)
                            continue
                    print(f"  [Balancer] {prov_name}/{try_model}: {str(e)[:80]}")
                    best_provider.mark_key_error(best_key, str(e)[:60], cooldown=60)
                    continue

        self._total_errors += 1
        return "⚠️ Все LLM-провайдеры временно недоступны. Проверьте квоты и API-ключи."

    def status(self) -> dict:
        result = {
            "total_requests": self._total_requests,
            "total_errors": self._total_errors,
            "providers": {},
        }
        for name, prov in self.providers.items():
            result["providers"][name] = {
                "keys_total": len(prov.keys),
                "keys_available": sum(1 for k in prov.keys if k.is_available),
                "requests": self._provider_stats.get(name, 0),
                "models": prov.models[:5],
            }
        return result
