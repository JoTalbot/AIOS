# Import necessary modules
import os
from typing import List

def scan_for_todo_fixme_hack(file_path: str) -> None:
    """
    Scans a Python file for TODO, FIXME, and HACK comments.
    
    Args:
        file_path (str): The path to the Python file to be scanned.
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
        
    # Check for TODO comments
    if "TODO" in content:
        print(f"Found TODO comment in {file_path}")
    
    # Check for FIXME comments
    if "FIXME" in content:
        print(f"Found FIXME comment in {file_path}")
    
    # Check for HACK comments
    if "HACK" in content:
        print(f"Found HACK comment in {file_path}")

def main() -> None:
    """
    Main function to run the code orchestrator.
    Scans a specified directory for Python files and checks for TODO, FIXME, and HACK comments.
    
    The script will output a message indicating whether each type of comment was found in any Python file.
    """
    target_directory = "tools/aios_v_fayle_run_183112.py"
    
    # Check if the directory exists
    if not os.path.exists(target_directory):
        print(f"Directory {target_directory} does not exist.")
        return
    
    # List all Python files in the directory
    python_files = [f for f in os.listdir(target_directory) if f.endswith('.py')]
    
    # Scan each Python file
    for file_name in python_files:
        file_path = os.path.join(target_directory, file_name)
        scan_for_todo_fixme_hack(file_path)

if __name__ == '__main__':
    main()