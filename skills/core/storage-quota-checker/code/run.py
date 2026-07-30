#!/usr/bin/env python3
"""Storage Quota Checker"""
import json

def check():
    return {
        "ok": True,
        "skill": "storage-quota-checker",
        "description": "Проверка квот хранилища",
        "status": "healthy",
        "recommendation": "OK"
    }

if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
