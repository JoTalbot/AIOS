#!/usr/bin/env python3
"""Octopus Skills MCP Stub (S02)"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "loader"))
from skills_loader import skills_loader

def handle(method, params):
    if method == "skills/list":
        return {"skills": skills_loader.list_metadata()}
    if method == "skills/get":
        return {"content": skills_loader.load_full(params.get("name"))}
    if method == "skills/activate":
        return {"result": skills_loader.activate_skill(params.get("name",""), params.get("context",""))}
    if method == "skills/references":
        return {"refs": skills_loader.load_references(params.get("name"))}
    return {"error": "unknown"}

if __name__ == "__main__":
    print(json.dumps({"methods": ["skills/list","skills/get","skills/activate","skills/references"]}))
