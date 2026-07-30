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
import json
import os
import time
import urllib.request
import urllib.error
import threading
from dataclasses import dataclass, field


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
        print(f"  [Balancer] Key {key.key[:8]}... cooled down {cooldown}s: {error}")


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
    }

    # Fallback chain: if primary model fails, try these
    MODEL_FALLBACKS = {
        "meta-llama/llama-4-maverick": [
            "mistralai/mistral-small-3.2-24b-instruct",
            "deepseek/deepseek-chat-v3-0324",
            "glm-4.5-flash",
        ],
        "mistralai/mistral-small-3.2-24b-instruct": [
            "meta-llama/llama-4-maverick",
            "glm-4.5-flash",
        ],
        "glm-4.5-flash": [
            "glm-4.7-flash",
            "meta-llama/llama-4-maverick",
        ],
    }

    def __init__(self):
        self.providers: dict[str, Provider] = {}
        self._load_from_env()
        self._total_requests = 0
        self._total_errors = 0
        self._provider_stats: dict[str, int] = {}

    def _load_from_env(self):
        """Load providers and keys from environment variables."""
        # OpenRouter keys
        or_keys = []
        # Primary key
        pk = os.environ.get("OPENROUTER_API_KEY", "")
        if pk:
            or_keys.append(APIKey(key=pk, provider="openrouter"))
        # Additional keys from env
        for i in range(1, 10):
            k = os.environ.get(f"OPENROUTER_API_KEY_{i}", "")
            if k:
                or_keys.append(APIKey(key=k, provider="openrouter"))

        if or_keys:
            self.providers["openrouter"] = Provider(
                name="openrouter",
                base_url=self.PROVIDERS["openrouter"]["base_url"],
                keys=or_keys,
                models=self.PROVIDERS["openrouter"]["models"],
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
             max_tokens: int = 2000, temperature: float = 0.3) -> str:
        """Send chat request with automatic balancing and failover."""
        self._total_requests += 1

        if not model:
            model = os.environ.get("LLM_MODEL", "meta-llama/llama-4-maverick")

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
            # Find providers that support this model
            for prov_name, provider in self.providers.items():
                api_key = provider.get_next_key()
                if not api_key:
                    continue

                try:
                    payload = json.dumps({
                        "model": try_model,
                        "messages": all_messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    }).encode()

                    req = urllib.request.Request(
                        provider.base_url,
                        data=payload,
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {api_key.key}",
                            "HTTP-Referer": "https://github.com/JoTalbot/AIOS",
                            "X-Title": "AIOS Coder Orchestrator",
                        },
                    )

                    with urllib.request.urlopen(req, timeout=120) as resp:
                        data = json.loads(resp.read())

                    # Success!
                    self._provider_stats[prov_name] = self._provider_stats.get(prov_name, 0) + 1

                    # Z.ai returns different format
                    if "choices" in data:
                        return data["choices"][0]["message"]["content"]
                    elif "data" in data and "choices" in data["data"]:
                        return data["data"]["choices"][0]["message"]["content"]
                    elif "result" in data:
                        return data["result"]
                    else:
                        # Try to extract any text
                        return json.dumps(data)[:500]

                except urllib.error.HTTPError as e:
                    error_body = ""
                    try:
                        error_body = e.read().decode()[:200]
                    except:
                        pass

                    last_error = f"{prov_name}/{try_model}: HTTP {e.code}"
                    print(f"  [Balancer] {last_error}")

                    if e.code in (402, 429):
                        # Rate limit or no credits — cool down this key
                        provider.mark_key_error(api_key, f"HTTP {e.code}", cooldown=300)
                    elif e.code == 404:
                        # Model not found on this provider — skip
                        break
                    elif e.code >= 500:
                        provider.mark_key_error(api_key, f"HTTP {e.code}", cooldown=60)
                    elif e.code == 401:
                        provider.mark_key_error(api_key, "Auth failed", cooldown=600)
                    continue

                except Exception as e:
                    last_error = f"{prov_name}/{try_model}: {str(e)[:80]}"
                    print(f"  [Balancer] {last_error}")
                    provider.mark_key_error(api_key, str(e)[:50], cooldown=60)
                    continue

        self._total_errors += 1
        return f"LLM Error: all providers failed. Last: {last_error}"

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
