import json, subprocess
from datetime import datetime, timezone

def get_docker_stats():
    r = subprocess.run(
        ['docker', 'stats', '--no-stream', '--format', '{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}|{{.MemPerc}}|{{.NetIO}}|{{.BlockIO}}'],
        capture_output=True, text=True, timeout=30
    )
    containers = []
    for line in r.stdout.strip().splitlines():
        if not line:
            continue
        parts = line.split('|')
        if len(parts) >= 6:
            containers.append({
                'name': parts[0],
                'cpu': parts[1],
                'mem_usage': parts[2],
                'mem_perc': parts[3],
                'net_io': parts[4],
                'block_io': parts[5],
            })
    return containers

def parse_mem(s):
    return s

def main():
    containers = get_docker_stats()
    print(json.dumps({'containers': containers}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
