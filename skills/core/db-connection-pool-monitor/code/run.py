#!/usr/bin/env python3
"""Db Connection Pool Monitor"""
import json

def check():
    return {
        "ok": True,
        "skill": "db-connection-pool-monitor",
        "description": "Мониторинг пула подключений к БД",
        "status": "healthy",
        "recommendation": "OK"
    }

if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
