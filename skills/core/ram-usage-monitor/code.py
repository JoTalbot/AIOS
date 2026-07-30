import os

def check_ram():
    print('--- Octopus RAM Usage Report ---')
    try:
        with open('/proc/meminfo', 'r') as f:
            lines = f.readlines()
        total = int(lines[0].split()[1]) / 1024 / 1024
        free = int(lines[2].split()[1]) / 1024 / 1024
        print(f'[OK] System RAM: {total:.2f}GB total, {free:.2f}GB free.')
    except:
        print('[FAIL] Could not read RAM info.')

if __name__ == '__main__':
    check_ram()
