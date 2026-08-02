#!/usr/bin/env python3
"""
Helper to add new free LLM keys to /root/AIOS/data/.llm_keys.json and /etc/aios/aios-auto-coder.env
Usage:
  python3 add_free_llm_key.py --provider groq --key gsk_xxx
  python3 add_free_llm_key.py --provider cerebras --key csk-xxx
  python3 add_free_llm_key.py --provider together --key xxx
  python3 add_free_llm_key.py --list
  python3 add_free_llm_key.py --test groq
"""
import argparse, json, os, sys
from pathlib import Path
import requests

KEYS_FILE = Path("/root/AIOS/data/.llm_keys.json")
ENV_FILE = Path("/etc/aios/aios-auto-coder.env")

PROVIDER_CFG = {
    "groq": {"url": "https://api.groq.com/openai/v1/chat/completions", "test_model": "llama-3.1-8b-instant"},
    "cerebras": {"url": "https://api.cerebras.ai/v1/chat/completions", "test_model": "llama-3.1-8b"},
    "mistral": {"url": "https://api.mistral.ai/v1/chat/completions", "test_model": "mistral-small-latest"},
    "cohere": {"url": "https://api.cohere.ai/v2/chat", "test_model": "command-r-08-2024"},
    "together": {"url": "https://api.together.xyz/v1/chat/completions", "test_model": "meta-llama/Meta-Llama-3-70B-Instruct-Turbo"},
    "gemini": {"url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", "test_model": "gemini-2.0-flash"},
    "openrouter": {"url": "https://openrouter.ai/api/v1/chat/completions", "test_model": "openai/gpt-oss-20b:free"},
    "deepseek": {"url": "https://api.deepseek.com/chat/completions", "test_model": "deepseek-chat"},
    "huggingface": {"url": "https://router.huggingface.co/v1/chat/completions", "test_model": "google/gemma-3-27b-it"},
    "github": {"url": "https://models.inference.ai.azure.com/chat/completions", "test_model": "openai/gpt-4o-mini"},
    "nvidia": {"url": "https://integrate.api.nvidia.com/v1/chat/completions", "test_model": "meta/llama-3.1-8b-instruct"},
    "zai": {"url": "https://api.z.ai/api/v1/chat/completions", "test_model": "glm-4.5-flash"},
}

def load_keys():
    if KEYS_FILE.exists():
        return json.loads(KEYS_FILE.read_text())
    return {}

def save_keys(data):
    KEYS_FILE.write_text(json.dumps(data, indent=2))
    print(f"Saved to {KEYS_FILE}")

def add_key(provider, key):
    data = load_keys()
    if provider not in data:
        data[provider] = []
    if key in data[provider]:
        print(f"Key already exists for {provider}")
        return
    data[provider].append(key)
    save_keys(data)
    # Also append to env file
    env_key = f"{provider.upper()}_API_KEY_{len(data[provider])}"
    # Special mapping
    mapping = {
        "groq": "GROQ_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "mistral": "MISTRAL_API_KEY",
        "cohere": "COHERE_API_KEY",
        "together": "TOGETHER_API_KEY",
        "cerebras": "CEREBRAS_API_KEY",
        "huggingface": "HUGGINGFACE_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "zai": "ZAI_API_KEY",
        "github": "GITHUB_API_KEY",
        "nvidia": "NVIDIA_API_KEY",
    }
    prefix = mapping.get(provider, f"{provider.upper()}_API_KEY")
    line = f"{prefix}_{len(data[provider])}={key}"
    # Check env file
    env_content = ENV_FILE.read_text() if ENV_FILE.exists() else ""
    if key not in env_content:
        with open(ENV_FILE, "a") as f:
            f.write(f"\n{line}\n")
        print(f"Added {line} to {ENV_FILE}")
    else:
        print("Key already in env file")

def test_provider(provider):
    cfg = PROVIDER_CFG.get(provider)
    if not cfg:
        print(f"Unknown provider {provider}, known: {list(PROVIDER_CFG.keys())}")
        return False
    data = load_keys()
    keys = data.get(provider, [])
    if not keys:
        # try env
        keys = [os.environ.get(f"{provider.upper()}_API_KEY_{i}") or os.environ.get(f"{provider.upper()}_API_KEY") for i in range(1,10)]
        keys = [k for k in keys if k]
    if not keys:
        print(f"No keys for {provider}")
        return False
    key = keys[0]
    print(f"Testing {provider} with key {key[:10]}... model {cfg['test_model']}")
    try:
        payload = {"model": cfg["test_model"], "messages": [{"role":"user","content":"Say OK, 1 word"}], "max_tokens": 5}
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        if provider == "gemini":
            # Gemini needs different format, skip
            print("Gemini test skipped (needs special format)")
            return True
        if provider == "cohere":
            payload = {"model": cfg["test_model"], "message": "Say OK"}
        r = requests.post(cfg["url"], json=payload, headers=headers, timeout=20)
        print(f"Status {r.status_code}: {r.text[:300]}")
        return r.status_code == 200
    except Exception as e:
        print(f"Test failed: {e}")
        return False

def list_keys():
    data = load_keys()
    for prov, keys in data.items():
        print(f"{prov}: {len(keys)} keys")
        for k in keys:
            print(f"  - {k[:12]}...{k[-4:]}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", help="Provider name")
    ap.add_argument("--key", help="API key")
    ap.add_argument("--list", action="store_true", help="List keys")
    ap.add_argument("--test", help="Test provider")
    args = ap.parse_args()
    if args.list:
        list_keys()
    elif args.provider and args.key:
        add_key(args.provider, args.key)
    elif args.test:
        test_provider(args.test)
    else:
        ap.print_help()
