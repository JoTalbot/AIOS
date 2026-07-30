import subprocess
import time

def check_latency():
    nodes = {'AWS-US': '54.154.186.15', 'Local-Hub': '127.0.0.1'}
    print('--- Octopus Swarm Network Latency Report ---')
    for name, ip in nodes.items():
        try:
            # Check port 22 latency instead of ping
            start = time.time()
            subprocess.run(['nc', '-z', '-w', '2', ip, '22'], check=True)
            latency = (time.time() - start) * 1000
            print(f'[OK] {name} ({ip}): {latency:.2f} ms')
        except:
            print(f'[FAIL] {name} ({ip}): UNREACHABLE')

if __name__ == '__main__':
    check_latency()
