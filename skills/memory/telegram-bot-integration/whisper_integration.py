#!/usr/bin/env python3
"""BATCH 70: Whisper integration for voice"""
import json, sys, os
from datetime import datetime, timezone

sys.path.insert(0, '/mnt/agents/-Octopus/skills/memory/pwa-file-exchange')
from memory_api import save_memory_item

WHISPER_URL = 'http://127.0.0.1:8091'

def transcribe_audio(audio_path):
    import subprocess
    try:
        result = subprocess.run(
            ['curl', '-s', '-X', 'POST', f'{WHISPER_URL}/transcribe',
             '-F', f'file=@{audio_path}'],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        return {'ok': False, 'error': result.stderr}
    except Exception as e:
        return {'ok': False, 'error': str(e)}

def remember_voice(user_id, audio_path):
    transcription = transcribe_audio(audio_path)
    text = transcription.get('text', '') if transcription.get('ok') else ''
    if not text:
        text = '[voice note]'
    item_id = str(__import__('uuid').uuid4())
    item = save_memory_item(item_id, 'voice', f'Telegram/{user_id}', text, tags=['telegram', 'voice'])
    return {'ok': True, 'action': 'remember', 'source': 'telegram_voice', 'item': item, 'transcription': text}

if __name__ == '__main__':
    print(json.dumps(remember_voice('user-1', '/tmp/test_voice.ogg'), ensure_ascii=False, indent=2))
