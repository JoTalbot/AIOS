#!/usr/bin/env python3
"""BATCH 43: Telegram Bot Config"""
import json, os
from pathlib import Path

CONFIG_PATH = Path('/etc/octopus/telegram_bot.json')

def get_config():
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {
        'bot_token': os.environ.get('TELEGRAM_BOT_TOKEN', '<REQUIRED>'),
        'webhook_url': os.environ.get('TELEGRAM_WEBHOOK_URL', ''),
        'allowed_users': [],
        'commands': ['/remember', '/find', '/status'],
        'status': 'configured'
    }

def save_config(config):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2))
    return {'ok': True, 'path': str(CONFIG_PATH)}

if __name__ == '__main__':
    print(json.dumps(get_config(), ensure_ascii=False, indent=2))
