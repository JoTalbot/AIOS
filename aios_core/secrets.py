import os
import re
from pathlib import Path
from cryptography.fernet import Fernet
from typing import List

def get_secret_paths() -> List[str]:
    """Get paths to all secret files in the project."""
    return [
        'config.ini',
        'secrets.json',
        'credentials.txt'
    ]

def decrypt_secret(encrypted_secret: str) -> str:
    """Decrypt a secret using Fernet.

    Args:
        encrypted_secret (str): Encrypted secret.

    Returns:
        str: Decrypted secret.
    """
    key = Fernet.generate_key()
    fernet = Fernet(key)
    try:
        decrypted_secret = fernet.decrypt(encrypted_secret.encode()).decode()
        return decrypted_secret
    except Exception as e:
        print(f"Error decrypting secret: {e}")
        return ""

def scan_files_for_secrets(file_paths: List[str]) -> List[str]:
    """Scan files for secrets.

    Args:
        file_paths (List[str]): List of file paths to scan.

    Returns:
        List[str]: List of discovered secrets.
    """
    secrets_found = []
    for file_path in file_paths:
        try:
            with open(file_path, 'r') as file:
                content = file.read()
                if "SECRET" in content or "API_KEY" in content:
                    secrets_found.append(file_path)
        except Exception as e:
            print(f"Error scanning file {file_path}: {e}")
    return secrets_found

def find_secrets_in_project() -> List[str]:
    """Find secrets in the project.

    Returns:
        List[str]: List of discovered secrets.
    """
    secret_paths = get_secret_paths()
    secrets_found = scan_files_for_secrets(secret_paths)
    return secrets_found

def scan_all_files_in_project() -> List[str]:
    """Scan all files in the project for secrets.

    Returns:
        List[str]: List of discovered secrets.
    """
    secret_paths = pathlib.Path('.').rglob('*')
    secrets_found = []
    for file_path in secret_paths:
        if file_path.is_file():
            try:
                with open(file_path, 'r') as file:
                    content = file.read()
                    if "SECRET" in content or "API_KEY" in content:
                        secrets_found.append(file_path)
            except Exception as e:
                print(f"Error scanning file {file_path}: {e}")
    return secrets_found

def find_all_secrets_in_project() -> List[str]:
    """Find all secrets in the project.

    Returns:
        List[str]: List of discovered secrets.
    """
    secret_paths = get_secret_paths()
    secrets_found = scan_files_for_secrets(secret_paths)
    all_secrets_found = scan_all_files_in_project()
    return list(set(secrets_found + all_secrets_found))

def scan_project_for_secrets() -> List[str]:
    """Scan all files in the project for secrets using regex patterns.

    This function scans all files in the project directory for common secret patterns
    such as API keys, passwords, tokens, etc. using regular expressions.

    Returns:
        List[str]: List of discovered secrets with their file paths.
    """
    # Common secret patterns
    secret_patterns = [
        r'api[_-]?key["\']?\s*[:=]\s*["\'][^"\']+["\']',
        r'password["\']?\s*[:=]\s*["\'][^"\']+["\']',
        r'secret["\']?\s*[:=]\s*["\'][^"\']+["\']',
        r'token["\']?\s*[:=]\s*["\'][^"\']+["\']',
        r'aws[_-]?access[_-]?key[_-]?id["\']?\s*[:=]\s*["\'][^"\']+["\']',
        r'aws[_-]?secret[_-]?access[_-]?key["\']?\s*[:=]\s*["\'][^"\']+["\']',
        r'github[_-]?token["\']?\s*[:=]\s*["\'][^"\']+["\']',
        r'github[_-]?pat["\']?\s*[:=]\s*["\'][^"\']+["\']',
        r'private[_-]?key["\']?\s*[:=]\s*["\'][^"\']+["\']',
        r'-----BEGIN (RSA|DSA|EC|OPENSSH|PGP) PRIVATE KEY-----',
        r'xox[baprs]-[0-9]{11}-[0-9]{11}-[0-9a-zA-Z]{24}',
        r'-----BEGIN ENCRYPTED PRIVATE KEY-----'
    ]

    secrets_found: Set[str] = set()

    # Compile patterns for better performance
    compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in secret_patterns]

    # Scan all files in the project
    for file_path in pathlib.Path('.').rglob('*'):
        if file_path.is_file():
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                    content = file.read()
                    for pattern in compiled_patterns:
                        matches = pattern.findall(content)
                        for match in matches:
                            # Clean up the match to get just the secret value
                            secret = match.split('=')[-1].strip().strip('"\'')
                            secrets_found.add(f"{file_path}: {secret}")
            except Exception as e:
                print(f"Error scanning file {file_path}: {e}")

    return sorted(secrets_found)

def find_secrets_in_all_files() -> List[str]:
    """Find secrets in all files in the project.

    Returns:
        List[str]: List of discovered secrets.
    """
    secret_paths = pathlib.Path('.').rglob('*')
    secrets_found = []
    for file_path in secret_paths:
        if file_path.is_file():
            try:
                with open(file_path, 'r') as file:
                    content = file.read()
                    if "SECRET" in content or "API_KEY" in content:
                        secrets_found.append(file_path)
            except Exception as e:
                print(f"Error scanning file {file_path}: {e}")
    return secrets_found

def scan_files_for_secrets_in_code() -> List[str]:
    """Scan all files in the project for secrets in code.

    Returns:
        List[str]: List of discovered secrets.
    """
    secret_patterns = [
        r'api[_-]?key["\']?\s*[:=]\s*["\'][^"\']+["\']',
        r'password["\']?\s*[:=]\s*["\'][^"\']+["\']',
        r'secret["\']?\s*[:=]\s*["\'][^"\']+["\']',
        r'token["\']?\s*[:=]\s*["\'][^"\']+["\']',
        r'aws[_-]?access[_-]?key[_-]?id["\']?\s*[:=]\s*["\'][^"\']+["\']',
        r'aws[_-]?secret[_-]?access[_-]?key["\']?\s*[:=]\s*["\'][^"\']+["\']',
        r'github[_-]?token["\']?\s*[:=]\s*["\'][^"\']+["\']',
        r'github[_-]?pat["\']?\s*[:=]\s*["\'][^"\']+["\']',
        r'private[_-]?key["\']?\s*[:=]\s*["\'][^"\']+["\']',
        r'-----BEGIN (RSA|DSA|EC|OPENSSH|PGP) PRIVATE KEY-----',
        r'xox[baprs]-[0-9]{11}-[0-9]{11}-[0-9a-zA-Z]{24}',
        r'-----BEGIN ENCRYPTED PRIVATE KEY-----'
    ]

    secrets_found: Set[str] = set()

    # Compile patterns for better performance
    compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in secret_patterns]

    # Scan all files in the project
    for file_path in pathlib.Path('.').rglob('*'):
        if file_path.is_file():
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                    content = file.read()
                    for pattern in compiled_patterns:
                        matches = pattern.findall(content)
                        for match in matches:
                            # Clean up the match to get just the secret value
                            secret = match.split('=')[-1].strip().strip('"\'')
                            secrets_found.add(f"{file_path}: {secret}")
            except Exception as e:
                print(f"Error scanning file {file_path}: {e}")

    return sorted(secrets_found)

def find_secrets_in_project_code() -> List[str]:
    """Find secrets in the project code.

    Returns:
        List[str]: List of discovered secrets.
    """
    return scan_files_for_secrets_in_code()

def main() -> None:
    all_secrets_found = find_all_secrets_in_project()
    print(f"Secrets found: {all_secrets_found}")

if __name__ == "__main__":
    main()