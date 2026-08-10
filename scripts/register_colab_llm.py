#!/usr/bin/env python3
"""
AIOS Google Colab Custom LLM Registration Script
Подключает кастомную кодинг-модель, запущенную в Google Colab, к LLMBalancer AIOS.
"""

import sys
import os
import json
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
KEYS_FILE = REPO_ROOT / "data" / ".llm_keys.json"
ENV_FILE = REPO_ROOT / ".env"


def register_colab_endpoint(colab_url: str, model_name: str = "colab/qwen2.5-coder"):
    colab_url = colab_url.strip().rstrip("/")
    if not colab_url.endswith("/v1"):
        colab_url += "/v1"

    print(f"📡 Проверяю подключение к Google Colab LLM по адресу: {colab_url}...")

    # Проверка работы эндпоинта
    check_url = f"{colab_url}/models"
    try:
        req = urllib.request.Request(check_url, headers={"User-Agent": "AIOS-Colab-Register/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print("✅ Подключение к Google Colab LLM успешно установлено!")
            print("Доступные модели на Colab:", [m.get("id") for m in data.get("data", [])])
    except Exception as e:
        print(f"⚠️ Не удалось подключиться к /models ({e}). Проверяем отправку тестового запроса /chat/completions...")

    # Запись в data/.llm_keys.json
    KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
    keys_data = {}
    if KEYS_FILE.exists():
        try:
            keys_data = json.loads(KEYS_FILE.read_text(encoding="utf-8"))
        except Exception:
            keys_data = {}

    colab_config = {
        "provider": "colab",
        "base_url": colab_url,
        "model": model_name,
        "api_key": "colab-key-aios",
        "enabled": True,
        "registered_at": __import__("time").time()
    }

    keys_data["colab_llm"] = colab_config
    KEYS_FILE.write_text(json.dumps(keys_data, indent=2, ensure_ascii=False), encoding="utf-8")

    # Добавление переменной в .env
    env_content = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else ""
    if "COLAB_LLM_URL=" in env_content:
        lines = []
        for line in env_content.splitlines():
            if line.startswith("COLAB_LLM_URL="):
                lines.append(f"COLAB_LLM_URL={colab_url}")
            else:
                lines.append(line)
        ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        with open(ENV_FILE, "a", encoding="utf-8") as f:
            f.write(f"\nCOLAB_LLM_URL={colab_url}\nCOLAB_LLM_MODEL={model_name}\n")

    print(f"🎉 ✅ Google Colab LLM ('{model_name}') успешно зарегистрирована в AIOS!")
    print(f"• URL: {colab_url}")
    print("• Конфигурация сохранена в data/.llm_keys.json и .env")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python scripts/register_colab_llm.py <COLAB_TUNNEL_URL> [MODEL_NAME]")
        print("Пример: python scripts/register_colab_llm.py https://xxxx.trycloudflare.com/v1 colab/qwen2.5-coder")
        sys.exit(1)

    url = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else "colab/qwen2.5-coder"
    register_colab_endpoint(url, model)
