#!/usr/bin/env python3
"""Octopus WebDAV Router (Instruction #54)
Mounts onto existing FastAPI app under /api/v1/memory/webdav.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import sys, base64
from pathlib import Path

sys.path.insert(0, '/mnt/agents/-Octopus/skills/memory')
from webdav_server import list_files, save_file, get_file

router = APIRouter(prefix='/api/v1/memory/webdav', tags=['webdav'])

@router.get('/files')
def webdav_list():
    return {'ok': True, 'files': list_files()}

@router.post('/upload')
def webdav_upload(filename: str, content_b64: str):
    result = save_file(filename, content_b64)
    if not result.get('ok'):
        raise HTTPException(status_code=400, detail=result.get('error'))
    return result

@router.get('/download/{filename}')
def webdav_download(filename: str):
    result = get_file(filename)
    if not result.get('ok'):
        raise HTTPException(status_code=404, detail='not_found')
    return JSONResponse(content={
        'ok': True,
        'filename': result['filename'],
        'size': result['size'],
        'content_b64': result['content_b64']
    })
