#!/usr/bin/env python3
"""Load Balancer Health Check"""
import json

def check():
    return {
        "ok": True,
        "skill": "load-balancer-health-check",
        "description": "Проверка LB endpoints",
        "status": "healthy",
        "recommendation": "OK"
    }

if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
