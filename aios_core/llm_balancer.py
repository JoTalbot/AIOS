"""
LLM Balancer — автоматическая балансировка между провайдерами и ключами.

Провайдеры:
  - OpenRouter (OpenAI-compatible)
  - Z.ai (Zhipu AI, OpenAI-compatible)

Алгоритм:
  1. Round-robin между ключами одного провайдера
  2. При 402/429/5xx — переключение на следующий ключ/провайдер
  3. Fallback-модели если основная недоступна
  4. Кэширование "мёртвых" ключей на 5 минут
"""
import contextlib
import json
import os
import time
import urllib.request
import urllib.error
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

    @property
    def is_available(self) -> bool:
        return time.time() > self.cooldown_until


@dataclass
class Provider:
    name: str
    base_url: str
    keys: list[APIKey] = field(default_factory=list)
    models: list[str] = field(default_factory=list)
    _key_index: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def get_next_key(self) -> APIKey | None:
        with self._lock:
            available = [k for k in self.keys if k.is_available]
            if not available:
                return None
            # Round-robin
            idx = self._key_index % len(available)
            self._key_index = idx + 1
            key = available[idx]
            key.last_used = time.time()
            return key

    def mark_key_error(self, key: APIKey, error: str, cooldown: int = 300):
        key.last_error = error
        key.error_count += 1
        key.cooldown_until = time.time() + cooldown
        print(f"  [Balancer] {key.provider} key cooled down {cooldown}s: {error}")
    installed: set = field(default_factory=set)

class LLMBalancer:
    """Auto-balancing LLM client across multiple providers and keys."""

    # Provider registry
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
                "gemma-2-9b",
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
        "local": {
            "base_url": os.environ.get("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1/chat/completions"),
            "models": [
                "qwen2.5-coder:14b",
                "qwen2.5-coder:1.5b",
                "qwen2.5-coder:7b",
                "deepseek-coder:6.7b",
                "qwen2.5-coder:32b",
            ],
        },
    }

    # Fallback chain: if primary model fails, try these
    MODEL_FALLBACKS = {
        "openai/gpt-oss-20b:free": [
            "cohere/north-mini-code:free",
            "google/gemma-4-31b-it:free",
            "nvidia/nemotron-3-super-120b-a12b:free",
            "poolside/laguna-s-2.1:free",
            "meta-llama/Meta-Llama-3-70B-Instruct-Turbo",
            "mistralai/mistral-small-3.2-24b-instruct",
        ],
        "meta-llama/llama-4-maverick": [
            "gemini-2.0-flash",
            "mistralai/mistral-small-3.2-24b-instruct",
            "gpt-4o-mini",
            "deepseek/deepseek-chat-v3-0324",
            "gpt-4.1-mini",
            "DeepSeek-R1",
            "glm-4.5-flash",
            "deepseek-chat",
        ],
        "gemini-2.0-flash": [
            "gemini-2.5-flash",
            "meta-llama/llama-4-maverick",
            "gpt-4o-mini",
            "mistralai/mistral-small-3.2-24b-instruct",
        ],
        "gemini-2.5-flash": [
            "gemini-2.0-flash",
            "meta-llama/llama-4-maverick",
            "gpt-4o-mini",
        ],
        "gpt-4o-mini": [
            "gpt-4o",
            "gemini-2.0-flash",
            "meta-llama/llama-4-maverick",
        ],
        "mistralai/mistral-small-3.2-24b-instruct": [
            "meta-llama/llama-4-maverick",
            "gemini-2.0-flash",
            "gpt-4o-mini",
            "glm-4.5-flash",
        ],
        "glm-4.5-flash": [
            "glm-4.7-flash",
            "gemini-2.0-flash",
            "meta-llama/llama-4-maverick",
        ],
        "deepseek-chat": [
            "deepseek-reasoner",
            "meta-llama/llama-4-maverick",
            "gpt-4o-mini",
            "glm-4.5-flash",
        ],
        "deepseek/deepseek-chat-v3-0324": [
            "deepseek-chat",
            "meta-llama/llama-4-maverick",
            "mistralai/mistral-small-3.2-24b-instruct",
            "gpt-4o-mini",
        ],
        "gpt-4o": [
            "gpt-4o-mini",
            "gemini-2.0-flash",
            "meta-llama/llama-4-maverick",
            "glm-4.5-flash",
        ],
        "gpt-4.1-mini": [
            "gpt-4o-mini",
            "gemini-2.0-flash",
            "meta-llama/llama-4-maverick",
        ],
        "deepseek-reasoner": [
            "deepseek-chat",
            "meta-llama/llama-4-maverick",
            "gpt-4o-mini",
        ],
        "deepseek-coder": [
            "deepseek-chat",
            "meta-llama/llama-4-maverick",
            "gpt-4o-mini",
        ],
        "glm-4.5": [
            "glm-4.5-flash",
            "glm-4.7-flash",
            "meta-llama/llama-4-maverick",
        ],
        "glm-4.7-flash": [
            "glm-4.5-flash",
            "gemini-2.0-flash",
            "meta-llama/llama-4-maverick",
        ],
        "glm-5": [
            "glm-4.7-flash",
            "glm-4.5-flash",
            "gemini-2.0-flash",
            "meta-llama/llama-4-maverick",
        ],
        "llama-3.3-70b-versatile": [
            "llama-3.1-8b-instant",
            "meta-llama/llama-4-maverick",
            "gemini-2.0-flash",
        ],
        "llama-3.1-8b-instant": [
            "mistral-small-latest",
            "command-r-08-2024",
            "llama-3.3-70b-versatile",
            "gemini-2.0-flash",
        ],
        "mixtral-8x7b-32768": [
            "llama-3.1-8b-instant",
            "mistralai/mistral-small-3.2-24b-instruct",
            "meta-llama/llama-4-maverick",
        ],
        "gemma2-9b-it": [
            "llama-3.1-8b-instant",
            "gemini-2.0-flash",
            "meta-llama/llama-4-maverick",
        ],
        "gemini-2.5-pro": [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "meta-llama/llama-4-maverick",
            "gpt-4o-mini",
        ],
        "gpt-3.5-turbo": [
            "meta-llama/llama-4-maverick",
            "mistralai/mistral-small-3.2-24b-instruct",
            "deepseek/deepseek-chat-v3-0324",
            "llama-3.1-8b-instant",
            "glm-4.5-flash",
            "gemini-2.0-flash",
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
        # Smart provider priority per task_type (fast/cheap first => token economy).
        self.task_priority = {
            # Simple/chat: fast cheap models first
            "chat": ["groq", "mistral", "cohere", "openrouter", "openai", "gemini"],
            # Coding: capable models
            "code": ["groq", "mistral", "cohere", "openrouter", "openai", "gemini"],
            # Analysis/long: robust providers
            "analysis": ["openrouter", "groq", "mistral", "openai", "gemini", "cohere"],
            # Default
            "general": ["groq", "mistral", "cohere", "openrouter", "openai", "gemini"],
        }

    def _load_from_env(self):
        """Load providers and keys from env plus the external runtime registry."""
        # Import runtime keys without putting secrets in source code or images.
        # The registry is mounted at /app/data in Docker and lives in data/ on host.
        for key_file in (Path("/app/data/.llm_keys.json"), Path(__file__).resolve().parents[1] / "data/.llm_keys.json"):
            try:
                runtime = json.loads(key_file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            env_prefix = {"openrouter": "OPENROUTER_API_KEY", "gemini": "GEMINI_API_KEY", "openai": "OPENAI_API_KEY", "deepseek": "DEEPSEEK_API_KEY", "zai": "ZAI_API_KEY", "cerebras": "CEREBRAS_API_KEY", "mistral": "MISTRAL_API_KEY", "cohere": "COHERE_API_KEY", "together": "TOGETHER_API_KEY"}
            for provider, keys in runtime.items():
                prefix = env_prefix.get(provider)
                if not prefix or not isinstance(keys, list):
                    continue
                for index, key in enumerate(keys, 1):
                    if key and not os.environ.get(f"{prefix}_{index}"):
                        os.environ[f"{prefix}_{index}"] = str(key)
        # OpenRouter keys
        or_keys = []
        # Primary key
        pk = os.environ.get("OPENROUTER_API_KEY", "")
        if pk:
            or_keys.append(APIKey(key=pk, provider="openrouter"))
        # Additional keys from env with value dedup
        for i in range(1, 10):
            k = os.environ.get(f"OPENROUTER_API_KEY_{i}", "")
            if k and not any(ek.key == k for ek in or_keys):
                or_keys.append(APIKey(key=k, provider="openrouter"))

        if or_keys:
            self.providers["openrouter"] = Provider(
                name="openrouter",
                base_url=self.PROVIDERS["openrouter"]["base_url"],
                keys=or_keys,
                models=self.PROVIDERS["openrouter"]["models"],
            )

        # Gemini keys
        gem_keys = []
        for i in range(1, 10):
            k = os.environ.get(f"GEMINI_API_KEY_{i}", "")
            if k:
                gem_keys.append(APIKey(key=k, provider="gemini"))
        gk = os.environ.get("GEMINI_API_KEY", "")
        if gk and not any(k.key == gk for k in gem_keys):
            gem_keys.append(APIKey(key=gk, provider="gemini"))

        if gem_keys:
            self.providers["gemini"] = Provider(
                name="gemini",
                base_url=self.PROVIDERS["gemini"]["base_url"],
                keys=gem_keys,
                models=self.PROVIDERS["gemini"]["models"],
            )

        # OpenAI keys
        oai_keys = []
        for i in range(1, 10):
            k = os.environ.get(f"OPENAI_API_KEY_{i}", "")
            if k:
                oai_keys.append(APIKey(key=k, provider="openai"))
        ok = os.environ.get("OPENAI_API_KEY", "")
        if ok and not any(k.key == ok for k in oai_keys):
            oai_keys.append(APIKey(key=ok, provider="openai"))

        if oai_keys:
            self.providers["openai"] = Provider(
                name="openai",
                base_url=self.PROVIDERS["openai"]["base_url"],
                keys=oai_keys,
                models=self.PROVIDERS["openai"]["models"],
            )

        groq_keys = []
        for i in range(1, 10):
            k = os.environ.get(f"GROQ_API_KEY_{i}", "")
            if k:
                groq_keys.append(APIKey(key=k, provider="groq"))
        gqk = os.environ.get("GROQ_API_KEY", "")
        if gqk and not any(k.key == gqk for k in groq_keys):
            groq_keys.append(APIKey(key=gqk, provider="groq"))

        if groq_keys:
            self.providers["groq"] = Provider(
                name="groq",
                base_url=self.PROVIDERS["groq"]["base_url"],
                keys=groq_keys,
                models=self.PROVIDERS["groq"]["models"],
            )

        # DeepSeek keys
        ds_keys = []
        for i in range(1, 10):
            k = os.environ.get(f"DEEPSEEK_API_KEY_{i}", "")
            if k:
                ds_keys.append(APIKey(key=k, provider="deepseek"))
        dk = os.environ.get("DEEPSEEK_API_KEY", "")
        if dk and not any(k.key == dk for k in ds_keys):
            ds_keys.append(APIKey(key=dk, provider="deepseek"))

        if ds_keys:
            self.providers["deepseek"] = Provider(
                name="deepseek",
                base_url=self.PROVIDERS["deepseek"]["base_url"],
                keys=ds_keys,
                models=self.PROVIDERS["deepseek"]["models"],
            )

        # Z.ai keys
        zai_keys = []
        for i in range(1, 10):
            k = os.environ.get(f"ZAI_API_KEY_{i}", "")
            if k:
                zai_keys.append(APIKey(key=k, provider="zai"))
        # Also check ZAI_API_KEY (single)
        zk = os.environ.get("ZAI_API_KEY", "")
        if zk and not any(k.key == zk for k in zai_keys):
            zai_keys.append(APIKey(key=zk, provider="zai"))

        if zai_keys:
            self.providers["zai"] = Provider(
                name="zai",
                base_url=self.PROVIDERS["zai"]["base_url"],
                keys=zai_keys,
                models=self.PROVIDERS["zai"]["models"],
            )

        # Cerebras keys
        cerebras_keys = []
        for i in range(1, 10):
            k = os.environ.get(f"CEREBRAS_API_KEY_{i}", "")
            if k:
                cerebras_keys.append(APIKey(key=k, provider="cerebras"))
        ck = os.environ.get("CEREBRAS_API_KEY", "")
        if ck and not any(k.key == ck for k in cerebras_keys):
            cerebras_keys.append(APIKey(key=ck, provider="cerebras"))

        if cerebras_keys:
            self.providers["cerebras"] = Provider(
                name="cerebras",
                base_url=self.PROVIDERS["cerebras"]["base_url"],
                keys=cerebras_keys,
                models=self.PROVIDERS["cerebras"]["models"],
            )

        # Mistral keys
        mistral_keys = []
        for i in range(1, 10):
            k = os.environ.get(f"MISTRAL_API_KEY_{i}", "")
            if k:
                mistral_keys.append(APIKey(key=k, provider="mistral"))
        mk = os.environ.get("MISTRAL_API_KEY", "")
        if mk and not any(k.key == mk for k in mistral_keys):
            mistral_keys.append(APIKey(key=mk, provider="mistral"))
        if mistral_keys:
            self.providers["mistral"] = Provider(
                name="mistral",
                base_url=self.PROVIDERS["mistral"]["base_url"],
                keys=mistral_keys,
                models=self.PROVIDERS["mistral"]["models"],
            )

        # Cohere keys
        cohere_keys = []
        for i in range(1, 10):
            k = os.environ.get(f"COHERE_API_KEY_{i}", "")
            if k:
                cohere_keys.append(APIKey(key=k, provider="cohere"))
        ck = os.environ.get("COHERE_API_KEY", "")
        if ck and not any(k.key == ck for k in cohere_keys):
            cohere_keys.append(APIKey(key=ck, provider="cohere"))
        if cohere_keys:
            self.providers["cohere"] = Provider(
                name="cohere",
                base_url=self.PROVIDERS["cohere"]["base_url"],
                keys=cohere_keys,
                models=self.PROVIDERS["cohere"]["models"],
            )

        # Together keys
        together_keys = []
        for i in range(1, 10):
            k = os.environ.get(f"TOGETHER_API_KEY_{i}", "")
            if k:
                together_keys.append(APIKey(key=k, provider="together"))
        tk = os.environ.get("TOGETHER_API_KEY", "")
        if tk and not any(k.key == tk for k in together_keys):
            together_keys.append(APIKey(key=tk, provider="together"))
        if together_keys:
            self.providers["together"] = Provider(
                name="together",
                base_url=self.PROVIDERS["together"]["base_url"],
                keys=together_keys,
                models=self.PROVIDERS["together"]["models"],
            )

        # Local (Ollama) - enabled only if LOCAL_LLM=1 and Ollama is reachable
        if os.environ.get("LOCAL_LLM", "") == "1":
            import urllib.request as _ur
            try:
                with _ur.urlopen("http://localhost:11434/api/tags", timeout=2) as _r:
                    _installed = {m["name"] for m in json.loads(_r.read().decode("utf-8", "ignore")).get("models", [])}
            except Exception:
                _installed = set()
            local_keys = [APIKey(key="local", provider="local")]
            self.providers["local"] = Provider(
                name="local",
                base_url=self.PROVIDERS["local"]["base_url"],
                keys=local_keys,
                models=self.PROVIDERS["local"]["models"],
                installed=_installed,
            )

    def add_key(self, provider: str, key: str):
        """Dynamically add an API key."""
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
        api_key = APIKey(key=key, provider=provider)
        self.providers[provider].keys.append(api_key)

    def chat(self, messages: list[dict], model: str = "", system: str = "",
             max_tokens: int = 2000, temperature: float = 0.3,
             task_type: str = "general") -> str:
        """Send chat request with automatic balancing and failover."""
        self._total_requests += 1

        if not model:
            model = os.environ.get("LLM_MODEL", "meta-llama/llama-4-maverick")

        # Token-economy cache: identical (system, messages) => reuse previous answer.
        if os.environ.get("LLM_CACHE", "1") == "1":
            _key = str((system or "", [tuple(sorted(m.items())) for m in messages if isinstance(m, dict) and "role" in m and "content" in m]))
            if _key in self._cache:
                return self._cache[_key]

        # Build model try list (primary + fallbacks)
        models_to_try = [model]
        fallbacks = self.MODEL_FALLBACKS.get(model, [])
        models_to_try.extend(fallbacks)

        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)

        last_error = ""

        for try_model in models_to_try:
            # Try ALL available keys across COMPATIBLE providers
            keys_tried = 0
            max_keys_to_try = sum(len(p.keys) for p in self.providers.values())

            while keys_tried < max_keys_to_try:
                # Get next available key from a provider that supports this model
                best_provider = None
                best_key = None
                # Build an ordered provider list. When LOCAL_LLM is on and the model
                # is installed locally, try 'local' FIRST (before cloud/OpenRouter).
                _local_first = (
                    os.environ.get("LOCAL_LLM", "") == "1"
                    and "local" in self.providers
                )
                # Smart ordering: task priority (fast/cheap first), then known providers
                _prio = self.task_priority.get(task_type, self.task_priority["general"])
                _providers = []
                for _n in _prio:
                    if _n in self.providers:
                        _providers.append((_n, self.providers[_n]))
                # Append any providers not in priority list
                for _n, _pr in self.providers.items():
                    if _n not in _prio:
                        _providers.append((_n, _pr))
                if _local_first:
                    _providers = [("local", self.providers["local"])] + [
                        (n, pr) for n, pr in _providers if n != "local"
                    ]

                for prov_name, provider in _providers:
                    # Check if this provider supports the model
                    model_supported = (
                        try_model in provider.models or
                        prov_name == "openrouter"  # OpenRouter supports everything
                        or (prov_name == "local" and
                            (try_model in getattr(provider, "installed", set()) or
                             any(try_model in i for i in getattr(provider, "installed", set()))))
                    )
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
                    payload = json.dumps({
                        "model": try_model,
                        "messages": all_messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    }).encode()

                    req = urllib.request.Request(
                        best_provider.base_url,
                        data=payload,
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {best_key.key}",
                            "HTTP-Referer": "https://github.com/JoTalbot/AIOS",
                            "X-Title": "AIOS Coder Orchestrator",
                        },
                    )

                    import requests as _req_lib
                    _resp = _req_lib.post(best_provider.base_url, json=json.loads(payload),
                                          headers=req.headers, timeout=300)
                    _resp.raise_for_status()
                    data = _resp.json()

                    # Check for application-level errors (Z.ai style)
                    if isinstance(data, dict):
                        if data.get("success") is False or (data.get("code") and data["code"] not in (0, 200, None)):
                            err_msg = data.get("msg") or data.get("message") or str(data.get("code"))
                            print(f"  [Balancer] {prov_name} app-error: {err_msg}")
                            best_provider.mark_key_error(best_key, f"app-error: {err_msg}", cooldown=300)
                            continue
                        if "error" in data:
                            err_msg = data["error"].get("message", str(data["error"]))[:60]
                            print(f"  [Balancer] {prov_name} error: {err_msg}")
                            best_provider.mark_key_error(best_key, f"error: {err_msg}", cooldown=300)
                            continue

                    # Success!
                    self._provider_stats[prov_name] = self._provider_stats.get(prov_name, 0) + 1
                    print(f"  [Balancer] OK: {prov_name}/{try_model}")

                    if "choices" in data and data["choices"]:
                        _c = data["choices"][0]["message"]["content"]
                        _out = _c if isinstance(_c, str) else ""
                        if _out and os.environ.get("LLM_CACHE", "1") == "1":
                            _key = str((system or "", [tuple(sorted(m.items())) for m in messages if isinstance(m, dict) and "role" in m and "content" in m]))
                            if len(self._cache) < self._cache_max:
                                self._cache[_key] = _out
                        return _out
                    elif "data" in data and isinstance(data["data"], dict) and "choices" in data["data"]:
                        return data["data"]["choices"][0]["message"]["content"]
                    elif "message" in data and isinstance(data.get("message"), dict):
                        _mc = data["message"].get("content")
                        if isinstance(_mc, list):
                            return "".join(x.get("text", "") for x in _mc if isinstance(x, dict))
                        return str(_mc or "")
                    elif "result" in data:
                        return str(data["result"])
                    else:
                        # Unknown format — skip this key
                        print(f"  [Balancer] {prov_name}: unknown response format")
                        best_provider.mark_key_error(best_key, "unknown format", cooldown=60)
                        continue

                except Exception as e:
                    # Handle HTTP-status errors from requests/httpx (status_code attr)
                    _code = getattr(getattr(e, "response", None), "status_code", None) or getattr(e, "code", None)
                    if _code:
                        code = int(_code)
                        last_error = f"{prov_name}/{try_model}: HTTP {code}"
                        print(f"  [Balancer] {last_error}")
                        if code in (402, 429):
                            cd = 300 if code == 402 else 60
                            best_provider.mark_key_error(best_key, f"HTTP {code}", cooldown=cd)
                            continue
                        elif code == 404:
                            break  # model not on this provider, try next model
                        elif code == 401:
                            best_provider.mark_key_error(best_key, "Auth failed", cooldown=600)
                            continue
                        elif code == 403:
                            body = str(getattr(getattr(e, "response", None), "text", "") or "")
                            label = "HTTP 403" + (f" / {body.split(':',1)[0][:80]}" if body else "")
                            cooldown = 900 if "1010" in body else 600
                            best_provider.mark_key_error(best_key, label, cooldown=cooldown)
                            continue
                        elif code >= 500:
                            best_provider.mark_key_error(best_key, f"HTTP {code}", cooldown=60)
                            continue
                        else:
                            best_provider.mark_key_error(best_key, f"HTTP {code}", cooldown=300)
                            continue
                    last_error = f"{prov_name}/{try_model}: {str(e)[:60]}"
                    print(f"  [Balancer] {last_error}")
                    best_provider.mark_key_error(best_key, str(e)[:50], cooldown=60)
                    continue


        self._total_errors += 1
        return "⚠️ Все LLM-провайдеры временно недоступны. Проверьте квоты и API-ключи."

    def status(self) -> dict:
        """Return balancer status."""
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
                "models": prov.models,
            }
            for k in prov.keys:
                result["providers"][name][f"key_{k.key[:8]}"] = {
                    "available": k.is_available,
                    "errors": k.error_count,
                    "last_error": k.last_error,
                }
        return result
