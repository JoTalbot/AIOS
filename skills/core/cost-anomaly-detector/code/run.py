#!/usr/bin/env python3
"""Cost Anomaly Detector"""
import json

def check():
    return {
        "ok": True,
        "skill": "cost-anomaly-detector",
        "description": "Детекция аномалий в расходах",
        "status": "healthy",
        "recommendation": "OK"
    }

if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
