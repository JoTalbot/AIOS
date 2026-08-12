import json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

def check_docker_hub_rate():
    try:
        r = subprocess.run(
            ['curl', '-sS', '-m', '5', 'https://hub.docker.com/v2/repositories/library/alpine/'],
            capture_output=True, text=True, timeout=8
        )
        remaining = 'unknown'
        return {'status': 'ok', 'rate_limit_remaining': remaining}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

def check_disk_pressure():
    try:
        usage = os.statvfs('/')
        free_gb = (usage.f_bavail * usage.f_frsize) / (1024**3)
        return {'status': 'ok', 'free_gb': round(free_gb, 1)}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

def check_memory_pressure():
    try:
        with open('/proc/meminfo') as f:
            lines = f.readlines()
        mem = {}
        for line in lines:
            if ':' in line:
                k, v = line.split(':', 1)
                mem[k.strip()] = v.strip()
        return {'status': 'ok', 'meminfo': {k: mem[k] for k in ['MemTotal', 'MemAvailable', 'SwapTotal'] if k in mem}}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

def check_swap_usage():
    try:
        with open('/proc/swaps') as f:
            lines = f.readlines()
        return {'status': 'ok', 'swaps': lines[1:] if len(lines) > 1 else []}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}

def main():
    results = {
        'docker_hub': check_docker_hub_rate(),
        'disk': check_disk_pressure(),
        'memory': check_memory_pressure(),
        'swap': check_swap_usage(),
    }
    print(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
