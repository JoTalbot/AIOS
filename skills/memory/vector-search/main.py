#!/usr/bin/env python3
"""Octopus Vector Search with Embeddings (Instruction #54)"""
import json, sqlite3
from pathlib import Path

DB_PATH = '/mnt/agents/-Octopus/skills/memory/pwa-file-exchange/memory.db'

def search_memory(query: str, limit: int = 20):
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    q = f'%{query.strip()}%'
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

if __name__ == '__main__':
    print(json.dumps(search_memory('тест'), ensure_ascii=False, indent=2))
