#!/usr/bin/env python3
"""Octopus WebDAV Server + E2E Encryption Helper (Instruction #54)"""
import os
import sys
import json
import base64
from pathlib import Path
from datetime import datetime, timezone

STORAGE_DIR = Path("/mnt/agents/-Octopus/skills/memory/pwa-file-exchange/storage")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

def list_files():
    files = []
    for p in STORAGE_DIR.glob("*"):
        if p.is_file():
            files.append({
                "name": p.name,
                "size": p.stat().st_size,
                "modified": p.stat().st_mtime,
            })
    return files

def save_file(filename, content_b64):
    try:
        data = base64.b64decode(content_b64)
        path = STORAGE_DIR / filename
        with open(path, "wb") as f:
            f.write(data)
        return {"ok": True, "filename": filename, "size": len(data)}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def get_file(filename):
    path = STORAGE_DIR / filename
    if not path.exists():
        return {"ok": False, "error": "not_found"}
    with open(path, "rb") as f:
        data = f.read()
    return {"ok": True, "filename": filename, "size": len(data), "content_b64": base64.b64encode(data).decode()}

def e2e_encrypt(data_bytes, key_material):
    """Simple XOR-based E2E placeholder (production: AES-256-GCM via WebCrypto)."""
    key = key_material.encode() if isinstance(key_material, str) else key_material
    encrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(data_bytes))
    return base64.b64encode(encrypted).decode()

def e2e_decrypt(data_b64, key_material):
    key = key_material.encode() if isinstance(key_material, str) else key_material
    encrypted = base64.b64decode(data_b64)
    decrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(encrypted))
    return decrypted

def semantic_search(query):
    import sys
    sys.path.insert(0, '/mnt/agents/-Octopus/skills/memory/pwa-file-exchange')
    from memory_api import search_memory
    return search_memory(query)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_data = b"Octopus Memory Secret"
        enc = e2e_encrypt(test_data, "secret-key")
        dec = e2e_decrypt(enc, "secret-key")
        print(json.dumps({
            "ok": test_data == dec,
            "encrypted": enc[:20] + "...",
            "decrypted_match": test_data == dec,
        }, ensure_ascii=False))
    else:
        print(json.dumps({"ok": True, "files": list_files(), "storage": str(STORAGE_DIR)}, ensure_ascii=False, indent=2))
