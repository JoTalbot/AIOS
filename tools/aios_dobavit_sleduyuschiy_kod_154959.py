# tools/aios_dobavit_sleduyuschiy_kod_154959.py

import os
import sys
from todo_scanner import todo_scanner

def add_todo_check():
    """
    Checks for TODO/FIXME/HACK comments in files and exits with non-zero status if found.
    
    This function is designed to be used in a CI/CD pipeline to prevent merge if there are any TODOs.
    """
    try:
        if os.environ.get('CI') == 'true':
            todos = todo_scanner.scan_files()
            if todos:
                print('Найдены незавершённые TODO/FIXME/HACK! Блокируем merge.')
                sys.exit(1)
    except Exception as e:
        print(f"Error checking for TODOs: {e}")

if __name__ == '__main__':
    add_todo_check()

__all__ = ['add_todo_check']