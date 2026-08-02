"""
AIOS LLM Key Checker v1.0
Реально проверяет каждый ключ каждого провайдера минимальным запросом.
Ничего не меняет — только отчёт.
"""
import json
import sys
import time

sys.path.insert(0, "/root/AIOS")

import requests  # noqa: E402

from aios_core.llm_balancer import LLMBalancer  # noqa: E402


def mask(key: str) -> str:
    if len(key) <= 8:
        return key[:3] + "***"
    return f"{key[:7]}...{key[-4:]}"


def check_key(prov_name: str, base_url: str, key: str, model: str) -> tuple[bool, str]:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
        "HTTP-Referer": "https://github.com/JoTalbot/AIOS",
    }
    if prov_name == "cohere":
        payload = {"model": model, "message": "Say OK", "max_tokens": 5}
    else:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "Say OK"}],
            "max_tokens": 5,
        }
    t0 = time.time()
    try:
        r = requests.post(base_url, json=payload, headers=headers, timeout=25)
        dt = time.time() - t0
        if r.status_code == 200:
            try:
                data = r.json()
                if isinstance(data, dict) and "error" in data:
                    return False, f"HTTP 200 но error: {str(data['error'])[:80]}"
            except ValueError:
                pass
            return True, f"OK ({dt:.1f}s)"
        body = r.text[:100].replace("\n", " ")
        return False, f"HTTP {r.status_code} ({dt:.1f}s): {body}"
    except requests.exceptions.Timeout:
        return False, f"TIMEOUT 25s"
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)[:80]}"


def main():
    print("=" * 78)
    print("AIOS LLM KEY CHECK — реальная проверка всех ключей")
    print("=" * 78)

    b = LLMBalancer()
    results = {}
    for name, prov in b.providers.items():
        if name == "local":
            continue
        model = prov.models[0] if prov.models else "gpt-4o-mini"
        ok_count = 0
        for i, k in enumerate(prov.keys, 1):
            ok, msg = check_key(name, prov.base_url, k.key, model)
            mark = "✅" if ok else "❌"
            print(f"{mark} {name:<12} ключ #{i} [{mask(k.key)}] модель={model:<28} {msg}")
            results.setdefault(name, []).append(ok)
            if ok:
                ok_count += 1
            time.sleep(0.5)  # не душим rate-limit

    print("=" * 78)
    print("СВОДКА ПО ПРОВАЙДЕРАМ (рабочих ключей / всего):")
    alive_providers = []
    for name, res in results.items():
        alive = sum(res)
        print(f"  {name:<12} {alive}/{len(res)} рабочих")
        if alive:
            alive_providers.append(name)
    print("=" * 78)
    if alive_providers:
        print(f"ЖИВЫЕ ПРОВАЙДЕРЫ: {', '.join(alive_providers)}")
    else:
        print("⚠️  НИ ОДИН ОБЛАЧНЫЙ ПРОВАЙДЕР НЕ РАБОТАЕТ — нужен fallback на local!")

    # Проверка local (Ollama)
    print("=" * 78)
    print("LOCAL (Ollama):")
    try:
        tags = requests.get("http://localhost:11434/api/tags", timeout=5).json()
        models = [m["name"] for m in tags.get("models", [])]
        print(f"  Ollama жива, модели: {models}")
        for m in ("aios-coder:7b", "qwen2.5-coder:7b"):
            if m in models:
                t0 = time.time()
                r = requests.post(
                    "http://localhost:11434/v1/chat/completions",
                    json={"model": m, "messages": [{"role": "user", "content": "Ответь одним словом: работаю"}], "max_tokens": 10},
                    timeout=120,
                )
                dt = time.time() - t0
                if r.status_code == 200:
                    txt = r.json()["choices"][0]["message"]["content"][:40]
                    print(f"  ✅ {m}: OK за {dt:.1f}s -> {txt!r}")
                else:
                    print(f"  ❌ {m}: HTTP {r.status_code}")
    except Exception as e:
        print(f"  ❌ Ollama недоступна: {e}")


if __name__ == "__main__":
    main()
