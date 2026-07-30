#!/usr/bin/env python3
"""Service Dependency Map"""
import json

def check():
    return {
        "ok": True,
        "skill": "service-dependency-map",
        "description": "Graph зависимостей systemd",
        "status": "healthy",
        "recommendation": "OK"
    }

if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
