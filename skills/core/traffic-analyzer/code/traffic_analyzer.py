import json, subprocess, sys, re
from datetime import datetime, timezone, timedelta
from collections import Counter
from pathlib import Path

NGINX_LOGS = [
    '/var/log/nginx/access.log',
    '/var/log/nginx/autosklo_access.log',
    '/var/log/nginx/autohelp_access.log',
]

def analyze_nginx_log(log_path, since_hours=24):
    if not Path(log_path).exists():
        return {'error': 'log not found'}
    try:
        with open(log_path) as f:
            lines = f.readlines()
        return {'lines': len(lines), 'path': log_path}
    except Exception as e:
        return {'error': str(e)}

def main():
    for log in NGINX_LOGS:
        if Path(log).exists():
            print(json.dumps(analyze_nginx_log(log), ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
