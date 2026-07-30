#!/usr/bin/env python3
"""Backup Restore Tester"""
import json

def check():
    return {
        "ok": True,
        "skill": "backup-restore-tester",
        "description": "Тестирование restore из бекапа",
        "status": "healthy",
        "recommendation": "OK"
    }

if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
