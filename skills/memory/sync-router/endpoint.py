#!/usr/bin/env python3
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import sys
sys.path.insert(0, '/mnt/agents/-Octopus/skills/memory/pwa-file-exchange')
from memory_api import save_memory_item

router = APIRouter(prefix='/api/v1/memory', tags=['sync'])

class SyncItem(BaseModel):
    id: str
    title: str
    content: str
    tags: List[str] = []
    modified_at: str

@router.post('/sync')
def memory_sync(items: List[SyncItem]):
    synced = 0
    conflicts = 0
    for item in items:
        try:
            save_memory_item(item.id, 'note', item.title, item.content, item.tags)
            synced += 1
        except Exception:
            conflicts += 1
    return {'ok': True, 'synced': synced, 'conflicts': conflicts}
