#!/usr/bin/env python3
"""Octopus Memory Upload Router (Instruction #54)"""
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import os, sys, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

router = APIRouter(prefix='/api/v1/memory', tags=['memory'])

STORAGE_DIR = Path('/mnt/agents/-Octopus/skills/memory/pwa-file-exchange/storage')
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = '/mnt/agents/-Octopus/skills/memory/pwa-file-exchange/memory.db'

def init_db():
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS memory_items (
        id TEXT PRIMARY KEY,
        item_type TEXT NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        tags TEXT,
        sha256 TEXT NOT NULL,
        created_at TEXT NOT NULL,
        modified_at TEXT NOT NULL,
        synced INTEGER DEFAULT 1
    )
    """)
    conn.commit()
    conn.close()

@router.post('/upload')
async def upload_file(file: UploadFile = File(...)):
    try:
        content = await file.read()
        sha = hashlib.sha256(content).hexdigest()
        item_id = sha[:16]
        now = datetime.now(timezone.utc).isoformat()
        storage_path = STORAGE_DIR / f'{item_id}_{file.filename}'
        with open(storage_path, 'wb') as f:
            f.write(content)
        init_db()
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""
        INSERT OR REPLACE INTO memory_items (id, item_type, title, content, tags, sha256, created_at, modified_at, synced)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (item_id, 'file', file.filename, '', file.filename, sha, now, now))
        conn.commit()
        conn.close()
        return {'ok': True, 'item_id': item_id, 'filename': file.filename, 'size': len(content), 'sha256': sha}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/files')
def list_files():
    files = []
    for p in STORAGE_DIR.glob('*'):
        if p.is_file():
            files.append({'name': p.name, 'size': p.stat().st_size})
    return {'ok': True, 'files': files}
