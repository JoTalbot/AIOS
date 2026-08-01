"""Compatibility bridge: aios_core.secrets -> aios_core.aios_secrets.

Some tests/history reference `from aios_core.secrets import SecretsManager`.
Re-export from the real module for backward compatibility.
"""
from __future__ import annotations
from typing import Optional
from dataclasses import dataclass
from aios_core.aios_secrets import SecretsManager, SecretVersion, RotationPolicy
import gitguardian
import secretscanner
import pathlib
import os

@dataclass
class SecretScannerResult:
    """Result of secret scanning."""
    secrets_found: list[str]
    scanner_used: str

class SecretScanner:
    """Class for scanning secrets in CI pipeline."""

    def __init__(self, scanner: object):
        self.scanner = scanner

    async def scan_secrets(self) -> SecretScannerResult:
        """Scan for secrets in the repository.

        Returns:
            SecretScannerResult: Result of secret scanning.
        """
        try:
            secrets_found = await self.scanner.scan()
            return SecretScannerResult(secrets_found, type(self.scanner).__name__)
        except Exception as e:
            print(f"Error scanning secrets with {type(self.scanner).__name__}: {e}")
            return SecretScannerResult([], type(self.scanner).__name__)

class SecretsScanner:
    """Class for scanning secrets in CI pipeline and integrating with SecretsManager."""

    def __init__(self, secret_scanner: SecretScanner, secrets_manager: SecretsManager):
        self.secret_scanner = secret_scanner
        self.secrets_manager = secrets_manager

    async def scan_and_store_secrets(self) -> None:
        """Scan for secrets in the repository and store them in SecretsManager."""
        result = await self.secret_scanner.scan_secrets()
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

def get_supported_scanners() -> list[str]:
    """Get list of supported secret scanners.

    Returns:
        list[str]: List of supported scanner names.
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

# A convenience instance named 'secrets' (as some callers expect).
secrets = SecretsManager()

# A convenience instance of SecretScannerFactory (as some callers expect).
secret_scanner_factory = SecretScannerFactory()

# A convenience instance of SecretSecurityChecker (as some callers expect).
secret_security_checker = get_secret_security_checker()

def scan_and_store_secrets_with_security_check(scanner_name: str = "gitguardian") -> None:
    """Scan for secrets in the repository with security check and store them in SecretsManager.

    Args:
        scanner_name (str, optional): Name of the scanner to use. Defaults to "gitguardian".
    """
    secret_scanner = get_secret_scanner(scanner_name)
    result = secret_scanner.scan_secrets()
    if result.secrets_found:
        print(f"Secrets found with {result.scanner_used}: {result.secrets_found}")
        for secret in result.secrets_found:
            if secret_security_checker.is_secret_path(secret):
                print(f"Skipping secret {secret} due to security check")
            else:
                await secrets.store_secrets([secret])

def get_secret_paths() -> list[str]:
    """Get list of secret paths.

    Returns:
        list[str]: List of secret paths.
    """
    return [str(path) for path in pathlib.Path('.').rglob('secret*')]

def main() -> None:
    secret_security_checker.add_secret_path(get_secret_paths()[0])
    scan_and_store_secrets_with_security_check()

def scan_secrets_with_gitguardian() -> None:
    """Scan for secrets in the repository with GitGuardian and store them in SecretsManager."""
    secret_scanner = get_secret_scanner("gitguardian")
    result = secret_scanner.scan_secrets()
    if result.secrets_found:
        print(f"Secrets found with GitGuardian: {result.secrets_found}")
        await secrets.store_secrets(result.secrets_found)

def scan_secrets_with_secretscanner() -> None:
    """Scan for secrets in the repository with SecretScanner and store them in SecretsManager."""
    secret_scanner = get_secret_scanner("secretscanner")
    result = secret_scanner.scan_secrets()
    if result.secrets_found:
        print(f"Secrets found with SecretScanner: {result.secrets_found}")
        await secrets.store_secrets(result.secrets_found)

if __name__ == "__main__":
    main()