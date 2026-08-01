"""Module for scanning secrets in the project.

This module provides functionality for scanning secrets in the project.
It uses various secret scanners to scan files for secrets and stores them in SecretsManager.
"""

from __future__ import annotations
from typing import Optional, List, Dict, Set
from dataclasses import dataclass
from aios_core.aios_secrets import SecretsManager, SecretVersion, RotationPolicy
from cryptography.fernet import Fernet
import gitguardian
import secretscanner
import pathlib
import os
import asyncio
import re
import ast

@dataclass
class SecretScannerResult:
    """Result of secret scanning."""
    secrets_found: List[str]
    scanner_used: str

class SecretScanner:
    """Class for scanning secrets in CI pipeline."""

    def __init__(self, scanner: object):
        self.scanner = scanner

    async def scan_secrets(self, root_dir: str = '.') -> SecretScannerResult:
        """Scan for secrets in the repository.

        Args:
            root_dir (str, optional): Root directory to scan. Defaults to '.'.

        Returns:
            SecretScannerResult: Result of secret scanning.
        """
        try:
            secrets_found = await self.scanner.scan(root_dir)
            return SecretScannerResult(secrets_found, type(self.scanner).__name__)
        except Exception as e:
            print(f"Error scanning secrets with {type(self.scanner).__name__}: {e}")
            return SecretScannerResult([], type(self.scanner).__name__)

class SecretsScanner:
    """Class for scanning secrets in CI pipeline and integrating with SecretsManager."""

    def __init__(self, secret_scanner: SecretScanner, secrets_manager: SecretsManager):
        self.secret_scanner = secret_scanner
        self.secrets_manager = secrets_manager

    async def scan_and_store_secrets(self, scanner_name: str = "gitguardian") -> None:
        """Scan for secrets in the repository and store them in SecretsManager.

        Args:
            scanner_name (str, optional): Name of the scanner to use. Defaults to "gitguardian".
        """
        result = await self.secret_scanner.scan_secrets(scanner_name)
        if result.secrets_found:
            print(f"Secrets found with {result.scanner_used}: {result.secrets_found}")
            await self.secrets_manager.store_secrets(result.secrets_found)

class SecretScannerFactory:
    """Factory for creating secret scanners."""

    def __init__(self):
        self.scanners = {
            "gitguardian": gitguardian.GitGuardian,
            "secretscanner": secretscanner.SecretScanner
        }

    def get_secret_scanner(self, scanner_name: str) -> SecretScanner:
        """Get instance of secret scanner.

        Args:
            scanner_name (str): Name of the scanner to use.

        Returns:
            SecretScanner: Instance of secret scanner.
        """
        if scanner_name not in self.scanners:
            raise ValueError(f"Unsupported scanner: {scanner_name}")
        return SecretScanner(self.scanners[scanner_name]())

class SecretSecurityChecker:
    """Class for checking secret security."""

    def __init__(self):
        self.secret_paths = []

    def add_secret_path(self, path: str) -> None:
        """Add secret path to check.

        Args:
            path (str): Path to secret file.
        """
        self.secret_paths.append(path)

    def is_secret_path(self, path: str) -> bool:
        """Check if path is secret.

        Args:
            path (str): Path to check.

        Returns:
            bool: True if path is secret, False otherwise.
        """
        return path in self.secret_paths

class SecretScannerService:
    """Class for scanning secrets in the repository and integrating with SecretsManager."""

    def __init__(self, secret_scanner_factory: SecretScannerFactory, secrets_manager: SecretsManager):
        self.secret_scanner_factory = secret_scanner_factory
        self.secrets_manager = secrets_manager

    async def scan_and_store_secrets(self, scanner_name: str = "gitguardian") -> None:
        """Scan for secrets in the repository with security check and store them in SecretsManager.

        Args:
            scanner_name (str, optional): Name of the scanner to use. Defaults to "gitguardian".
        """
        secret_scanner = self.secret_scanner_factory.get_secret_scanner(scanner_name)
        result = await secret_scanner.scan_secrets(scanner_name)
        if result.secrets_found:
            print(f"Secrets found with {result.scanner_used}: {result.secrets_found}")
            secret_security_checker = SecretSecurityChecker()
            for secret in result.secrets_found:
                if secret_security_checker.is_secret_path(secret):
                    print(f"Skipping secret {secret} due to security check")
                else:
                    await self.secrets_manager.store_secrets([secret])

class SecretScannerServiceFactory:
    """Factory for creating secret scanner services."""

    def __init__(self):
        self.secret_scanner_factories = {
            "gitguardian": SecretScannerFactory,
            "secretscanner": SecretScannerFactory
        }
        self.secrets_manager = SecretsManager()

    def get_secret_scanner_service(self, scanner_name: str) -> SecretScannerService:
        """Get instance of secret scanner service.

        Args:
            scanner_name (str): Name of the scanner to use.

        Returns:
            SecretScannerService: Instance of secret scanner service.
        """
        if scanner_name not in self.secret_scanner_factories:
            raise ValueError(f"Unsupported scanner: {scanner_name}")
        return SecretScannerService(self.secret_scanner_factories[scanner_name](), self.secrets_manager)

def get_supported_scanners() -> List[str]:
    """Get list of supported secret scanners.

    Returns:
        List[str]: List of supported scanner names.
    """
    return list(SecretScannerFactory().scanners.keys())

def get_secret_scanner(scanner_name: str) -> SecretScanner:
    """Get instance of secret scanner.

    Args:
        scanner_name (str): Name of the scanner to use.

    Returns:
        SecretScanner: Instance of secret scanner.
    """
    if scanner_name not in SecretScannerFactory().scanners:
        raise ValueError(f"Unsupported scanner: {scanner_name}")
    return SecretScannerFactory().get_secret_scanner(scanner_name)

def get_secret_security_checker() -> SecretSecurityChecker:
    """Get instance of secret security checker.

    Returns:
        SecretSecurityChecker: Instance of secret security checker.
    """
    return SecretSecurityChecker()

def scan_and_store_secrets_with_security_check(scanner_name: str = "gitguardian") -> None:
    """Scan for secrets in the repository with security check and store them in SecretsManager.

    Args:
        scanner_name (str, optional): Name of the scanner to use. Defaults to "gitguardian".
    """
    secret_scanner_service = get_secret_scanner_service(scanner_name)
    asyncio.run(secret_scanner_service.scan_and_store_secrets(scanner_name))

def get_secret_paths() -> List[str]:
    """Get list of secret paths.

    Returns:
        List[str]: List of secret paths.
    """
    return [str(path) for path in pathlib.Path('.').rglob('secret*')]

def get_secret_scanner_service(scanner_name: str) -> SecretScannerService:
    """Get instance of secret scanner service.

    Args:
        scanner_name (str): Name of the scanner to use.

    Returns:
        SecretScannerService: Instance of secret scanner service.
    """
    if scanner_name not in SecretScannerServiceFactory().secret_scanner_factories:
        raise ValueError(f"Unsupported scanner: {scanner_name}")
    return SecretScannerServiceFactory().get_secret_scanner_service(scanner_name)

def scan_secrets_with_gitguardian() -> None:
    """Scan for secrets in the repository with GitGuardian and store them in SecretsManager."""
    secret_scanner_service = get_secret_scanner_service("gitguardian")
    asyncio.run(secret_scanner_service.scan_and_store_secrets("gitguardian"))

def scan_secrets_with_secretscanner() -> None:
    """Scan for secrets in the repository with SecretScanner and store them in SecretsManager."""
    secret_scanner_service = get_secret_scanner_service("secretscanner")
    asyncio.run(secret_scanner_service.scan_and_store_secrets("secretscanner"))

def scan_all_files_for_secrets() -> List[str]:
    """Scan all files in the repository for secrets.

    Returns:
        List[str]: List of discovered secrets.
    """
    secret_scanner_service = get_secret_scanner_service("gitguardian")
    result = asyncio.run(secret_scanner_service.scan_secrets("gitguardian"))
    if result.secrets_found:
        return result.secrets_found
    else:
        return []

def encrypt_secret(secret: str) -> str:
    """Encrypt secret using Fernet.

    Args:
        secret (str): Secret to encrypt.

    Returns:
        str: Encrypted secret.
    """
    key = Fernet.generate_key()
    fernet = Fernet(key)
    encrypted_secret = fernet.encrypt(secret.encode())
    return encrypted_secret.decode()

def decrypt_secret(encrypted_secret: str) -> str:
    """Decrypt secret using Fernet.

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

def scan_files_for_secrets_in_project() -> List[Dict[str, str]]:
    """Scan all files in the project for secrets.

    Returns:
        List[Dict[str, str]]: List of discovered secrets with their types.
    """
    secret_paths = get_secret_paths()
    secrets_found = scan_files_for_secrets(secret_paths)
    secrets_with_types = []
    for secret in secrets_found:
        secret_type = "Unknown"
        if "SECRET" in secret:
            secret_type = "SECRET"
        elif "API_KEY" in secret:
            secret_type = "API_KEY"
        secrets_with_types.append({"тип секрета": secret_type, "значение секрета": secret})
    return secrets_with_types

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