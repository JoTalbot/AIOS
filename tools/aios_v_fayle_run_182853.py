# run_coder_orchestrator.py

import os
import re

def scan_files_for_tags(target_path, tags):
    todos = []
    for root, dirs, files in os.walk(target_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for tag in tags:
                        matches = re.findall(rf'{tag}:', content)
                        todos.extend(matches)
    return todos

def main():
    target_path = 'tools/aios_v_fayle_run_182853.py'
    tags = ['TODO', 'FIXME', 'HACK', 'XXX', 'BUG']
    
    try:
        todos = scan_files_for_tags(target_path, tags)
        print("Found TODO/FIXME/HACK in Python files:")
        for todo in todos:
            print(todo)
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    main()