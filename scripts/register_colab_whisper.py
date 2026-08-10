#!/usr/bin/env python3
"""
AIOS Register Colab Whisper Tunnel Endpoint
Регистрирует публичную ссылку Cloudflare-туннеля из Colab Whisper сервера в конфигурацию AIOS.
"""

import os
import sys
import json
import requests
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WHISPER_KEY_FILE = REPO_ROOT / "data" / "colab_whisper_url.json"


def register_whisper_endpoint(url: str):
    url = url.rstrip('/')
    print(f"📡 Проверка связи с Colab Whisper сервером по адресу: {url}...")

    try:
        resp = requests.get(f"{url}/health", timeout=10)
        if resp.status_code == 200 and resp.json().get("status") == "ok":
            health_data = resp.json()
            data = {
                "url": url,
                "model": health_data.get("model", "large-v3"),
                "status": "online",
                "free_tier": True,
                "updated_at": requests.get("https://worldtimeapi.org/api/timezone/Etc/UTC").json().get("datetime", "") if False else ""
            }
            WHISPER_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(WHISPER_KEY_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Также обновляем .env при наличии
            env_file = REPO_ROOT / ".env"
            if env_file.exists():
                content = env_file.read_text(encoding="utf-8")
                if "COLAB_WHISPER_URL=" in content:
                    lines = content.splitlines()
                    new_lines = [f"COLAB_WHISPER_URL={url}" if l.startswith("COLAB_WHISPER_URL=") else l for l in lines]
                    env_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
                else:
                    with open(env_file, "a", encoding="utf-8") as f:
                        f.write(f"\nCOLAB_WHISPER_URL={url}\n")

            print(f"🎉 [УСПЕХ] Colab Whisper GPU сервер зарегистрирован!")
            print(f"   URL: {url}")
            print(f"   Модель: {health_data.get('model', 'large-v3')} (T4 GPU)")
            return True
        else:
            print(f"❌ Сервер ответил со статусом {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        print(f"❌ Не удалось подключиться к Colab Whisper: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python3 scripts/register_colab_whisper.py <https://xxxx.trycloudflare.com>")
        sys.exit(1)

    target_url = sys.argv[1].strip()
    success = register_whisper_endpoint(target_url)
    sys.exit(0 if success else 1)
