"""
Module for scanning secrets in project files.
"""

import os
from aios_scanfortagsrootdir_str_listdict_115420 import scan_for_tags

__all__ = ['scan_for_secrets']

@dataclass
class Secret:
    """Class for storing secret information."""
    file_path: str
    secret: str

async def scan_for_secrets(root_dir: str) -> list[Secret]:
    """
    Scan for secrets in all files in the project.

    Args:
    root_dir (str): The root directory of the project.

    Returns:
    list[Secret]: A list of secrets found in the project files.
    """
    try:
        # Get a list of all files in the project
        files = await scan_for_tags(root_dir)
        
        # Initialize an empty list to store secrets
        secrets = []
        
        # Iterate over each file
        for file in files:
            # Open the file and read its contents
            with open(file, 'r') as f:
                contents = f.read()
            
            # Use regular expression to find secrets in the file contents
            # For simplicity, let's assume secrets are strings that start with 'SECRET_'
            import re
            secrets_in_file = re.findall(r'SECRET_(\w+)', contents)
            
            # Add the secrets found in the file to the list
            secrets.extend([Secret(file, secret) for secret in secrets_in_file])
        
        return secrets
    
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return []
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

if __name__ == '__main__':
    # Test the function
    root_dir = os.path.dirname(os.path.abspath(__file__))
    secrets = scan_for_secrets(root_dir)
    print(secrets)