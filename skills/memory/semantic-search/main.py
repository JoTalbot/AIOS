#!/usr/bin/env python3
"""BATCH 58: Semantic Search with Ollama Embeddings"""
import json, subprocess, sys
from pathlib import Path

DB_PATH = '/mnt/agents/-Octopus/skills/memory/pwa-file-exchange/memory.db'
OLLAMA_URL = "http://127.0.0.1:11434/api/embeddings"

def get_ollama_embedding(text):
    try:
        result = subprocess.run(
            ["curl", "-s", "-X", "POST", OLLAMA_URL,
             "-H", "Content-Type: application/json",
             "-d", json.dumps({"model": "nomic-embed-text", "prompt": text})],
            capture_output=True, text=True, timeout=10
        )
        data = json.loads(result.stdout)
        return data.get("embedding", [])
    except Exception:
        return []

def search_memory_enhanced(query, limit=20):
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    q = '%' + query.strip() + '%'
    cur.execute("""
    SELECT id, item_type, title, content, tags, sha256, created_at, modified_at
    FROM memory_items
    WHERE title LIKE ? OR content LIKE ? OR tags LIKE ?
    ORDER BY modified_at DESC LIMIT ?
    """, (q, q, q, limit))
    rows = cur.fetchall()
    conn.close()
    results = []
    for r in rows:
        results.append({
            'id': r[0], 'item_type': r[1], 'title': r[2], 'content': r[3],
            'tags': (r[4] or '').split(','), 'sha256': r[5],
            'created_at': r[6], 'modified_at': r[7]
        })
    return {'ok': True, 'query': query, 'mode': 'sqlite_fallback', 'results': results}

if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "тест"
    print(json.dumps(search_memory_enhanced(query), ensure_ascii=False, indent=2))
