#!/usr/bin/env python3
import json, os, subprocess
from pathlib import Path

CONFIG_PATH = Path('/etc/octopus/telegram_bot.json')

def setup_webhook():
    config = json.loads(CONFIG_PATH.read_text()) if CONFIG_PATH.exists() else {}
    token = config.get('bot_token', os.environ.get('TELEGRAM_BOT_TOKEN', ''))
    webhook_url = config.get('webhook_url', 'https://178.105.142.113/webhook/telegram')

    if not token or token == '<REQUIRED>':
        return {'ok': False, 'error': 'TELEGRAM_BOT_TOKEN required', 'hint': 'Set TELEGRAM_BOT_TOKEN env var or edit /etc/octopus/telegram_bot.json'}

    result = subprocess.run([
        'curl', '-s', '-X', 'POST',
        f'https://api.telegram.org/bot{token}/setWebhook',
        '-H', 'Content-Type: application/json',
        '-d', json.dumps({'url': webhook_url, 'allowed_updates': ['message']})
    ], capture_output=True, text=True, timeout=10)

    return {'ok': True, 'webhook': json.loads(result.stdout), 'url': webhook_url}

if __name__ == '__main__':
    print(json.dumps(setup_webhook(), ensure_ascii=False, indent=2))
