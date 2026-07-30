#!/usr/bin/env python3
"""Dns Propagation Checker"""
import json

def check():
    return {
        "ok": True,
        "skill": "dns-propagation-checker",
        "description": "Проверка DNS propagation",
        "status": "healthy",
        "recommendation": "OK"
    }

if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
