import os
import shutil
import subprocess
import json

def run_janitor():
    cleaned = 0
    try:
        subprocess.check_call(['journalctl', '--vacuum-size=200M'])
    except Exception:
        pass
    try:
        subprocess.check_call(['find', '/tmp', '-type', 'f', '-mtime', '+7', '-delete'])
    except Exception:
        pass
    return cleaned

def main():
    cleaned = run_janitor()
    print(json.dumps({'cleaned': cleaned}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
