import subprocess

def report_software():
    print('--- Octopus Software Environment Report ---')
    tools = ['python3', 'rsync', 'git', 'docker']
    for t in tools:
        try:
            ver = subprocess.check_output([t, '--version'], text=True).split('\n')[0]
            print(f'[OK] {t}: {ver}')
        except:
            print(f'[MISSING] {t}')

if __name__ == '__main__':
    report_software()
