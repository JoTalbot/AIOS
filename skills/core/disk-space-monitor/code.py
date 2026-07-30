import subprocess

def check_disk():
    print('--- Octopus Disk Usage Report ---')
    try:
        res = subprocess.check_output(['df', '-h', '/'], text=True).split('\n')[1]
        parts = res.split()
        usage = parts[4]
        free = parts[3]
        print(f'[OK] Root Disk: {usage} used, {free} free.')
    except:
        print('[FAIL] Could not read disk usage.')

if __name__ == '__main__':
    check_disk()
