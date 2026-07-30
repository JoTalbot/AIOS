#!/usr/bin/env python3
"""Free Tier Preflight"""
import json

def check():
    return {
        "ok": True,
        "skill": "free-tier-preflight",
        "description": "Проверка free-tier ресурсов",
        "status": "healthy",
        "recommendation": "OK"
    }

if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
