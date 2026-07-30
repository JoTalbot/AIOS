#!/usr/bin/env python3
"""BATCH 59: Telegram Bot Webhook Integration"""
import json, os, sys
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, '/mnt/agents/-Octopus/skills/memory/pwa-file-exchange')
from memory_api import save_memory_item, search_memory

class TelegramHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(content_length))
        message = body.get('message', {})
        text = message.get('text', '')
        chat_id = message.get('chat', {}).get('id', '')

        if text.startswith('/remember'):
            _, _, content = text.partition(' ')
            content = content.strip() or 'Заметка из Telegram'
            item = save_memory_item(str(__import__('uuid').uuid4()), 'note', f'Telegram/{chat_id}', content, tags=['telegram'])
            response = {'ok': True, 'action': 'remember', 'item': item}
        elif text.startswith('/find'):
            _, _, query = text.partition(' ')
            results = search_memory(query.strip() or 'тест')
            response = {'ok': True, 'action': 'find', 'results': results.get('results', [])[:5]}
        else:
            response = {'ok': True, 'message': 'Octopus Memory Bot. Commands: /remember, /find'}

        self.send_json(response)

    def do_GET(self):
        self.send_json({'ok': True, 'service': 'telegram-bot-stub', 'status': 'running'})

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a): pass

if __name__ == '__main__':
    port = 8097
    server = HTTPServer(('127.0.0.1', port), TelegramHandler)
    print(f'Telegram Bot Stub on port {port}')
    server.serve_forever()
