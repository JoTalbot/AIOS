import re
import os

__all__ = ['remove_todo_comments', 'scan_todo_comments']

def remove_todo_comments(file_path: str) -> None:
    """
    Removes TODO/FIXME/HACK comments from a given Python file.

    Args:
    file_path (str): Path to the Python file.
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
        
        # Remove TODO/FIXME/HACK comments
        cleaned_lines = [line for line in lines if not re.search(r'#\s*(TODO|FIXME|HACK)', line)]
        
        # Write cleaned lines back to the file
        with open(file_path, 'w') as file:
            file.writelines(cleaned_lines)
        
        print(f"Comments removed from {file_path}")
    
    except FileNotFoundError:
        print(f"File {file_path} not found")
    
    except Exception as e:
        print(f"An error occurred: {e}")

def scan_todo_comments(directory: str) -> None:
    """
    Scans a directory for Python files and removes TODO/FIXME/HACK comments.

    Args:
    directory (str): Path to the directory.
    """
    try:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    remove_todo_comments(file_path)
    
    except Exception as e:
        print(f"An error occurred: {e}")

def remove_lines(file_path: str, start_line: int, end_line: int) -> None:
    """
    Removes lines from a given Python file.

    Args:
    file_path (str): Path to the Python file.
    start_line (int): Start line number (1-indexed).
    end_line (int): End line number (1-indexed).
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
        
        # Remove lines
        cleaned_lines = lines[:start_line-1] + lines[end_line:]
        
        # Write cleaned lines back to the file
        with open(file_path, 'w') as file:
            file.writelines(cleaned_lines)
        
        print(f"Lines removed from {file_path}")
    
    except FileNotFoundError:
        print(f"File {file_path} not found")
    
    except Exception as e:
        print(f"An error occurred: {e}")

def main() -> None:
    """
    Tests the functions.
    """
    remove_todo_comments('tools/aios_udalit_stroki_kotorye_160813.py')
    scan_todo_comments('tools')
    remove_lines('tools/aios_udalit_stroki_kotorye_160813.py', 147, 158)

if __name__ == '__main__':
    main()