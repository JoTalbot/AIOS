#!/usr/bin/env python3
"""Octopus WebDAV HTTP Server (Instruction #54)"""
import json, os, sys, base64
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

sys.path.insert(0, '/mnt/agents/-Octopus/skills/memory')
from webdav_server import list_files, save_file, get_file

STORAGE_DIR = Path('/mnt/agents/-Octopus/skills/memory/pwa-file-exchange/storage')
PORT = 8096

class WebDAVHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_json({'ok': True, 'service': 'webdav', 'port': PORT})
        elif self.path == '/files':
            self.send_json({'ok': True, 'files': list_files()})
        elif self.path.startswith('/download/'):
            filename = self.path.replace('/download/', '')
            result = get_file(filename)
            if not result.get('ok'):
                self.send_json({'error': 'not_found'}, 404)
                return
            self.send_response(200)
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(base64.b64decode(result['content_b64']))
        else:
            self.send_json({'error': 'not_found'}, 404)

    def do_POST(self):
        if self.path == '/upload':
            content_length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(content_length))
            result = save_file(body.get('filename'), body.get('content_b64'))
            self.send_json(result)
        else:
            self.send_json({'error': 'not_found'}, 404)

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a): pass

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', PORT), WebDAVHandler)
    print(f'WebDAV Server on port {PORT}')
    server.serve_forever()
