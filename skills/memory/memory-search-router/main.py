#!/usr/bin/env python3
"""Octopus Memory Search FastAPI Router (Instruction #54)
Adds /api/v1/memory/search endpoint to existing FastAPI app.
"""
from fastapi import APIRouter, Query, HTTPException
from typing import List
import sys

sys.path.insert(0, '/mnt/agents/-Octopus/skills/memory/pwa-file-exchange')
from memory_api import search_memory

router = APIRouter(prefix='/api/v1/memory', tags=['memory'])

@router.get('/search')
def memory_search(q: str = Query('', min_length=1), limit: int = Query(20, ge=1, le=100)):
    if not q.strip():
        raise HTTPException(status_code=400, detail='query required')
    results = search_memory(q, limit=limit)
    return {'ok': True, 'query': q, 'mode': 'sqlite_fallback', 'results': results}
