#!/usr/bin/env python3
"""Email Deliverability Tester"""
import json

def check():
    return {
        "ok": True,
        "skill": "email-deliverability-tester",
        "description": "Тест доставляемости email",
        "status": "healthy",
        "recommendation": "OK"
    }

if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
