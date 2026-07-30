import json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

REPUTATION_FILE = Path('/mnt/agents/-Octopus/data/node_reputation.json')

def read_reputation_file():
    if REPUTATION_FILE.exists():
        try:
            return json.loads(REPUTATION_FILE.read_text())
        except:
            pass
    return {}

def get_docker_node_info():
    try:
        r = subprocess.run(['docker', 'info', '--format', '{{json .}}'], capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            return [json.loads(r.stdout)]
    except Exception:
        pass
    return []

def main():
    rep = read_reputation_file()
    nodes = get_docker_node_info()
    print(json.dumps({'reputation': rep, 'nodes': nodes}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
