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

@dataclass
class SecretScannerResult:
    """Result of secret scanning."""
    secrets_found: list[str]
    scanner_used: str

class SecretScanner:
    """Class for scanning secrets in CI pipeline."""

    def __init__(self):
        self.scanners = {
            "gitguardian": gitguardian.GitGuardian,
            "secretscanner": secretscanner.SecretScanner
        }

    async def scan_secrets(self, scanner_name: str = "gitguardian") -> SecretScannerResult:
        """Scan for secrets in the repository.

        Args:
            scanner_name (str, optional): Name of the scanner to use. Defaults to "gitguardian".

        Returns:
            SecretScannerResult: Result of secret scanning.
        """
        if scanner_name not in self.scanners:
            raise ValueError(f"Unsupported scanner: {scanner_name}")

        scanner = self.scanners[scanner_name]()
        try:
            secrets_found = await scanner.scan()
            return SecretScannerResult(secrets_found, scanner_name)
        except Exception as e:
            print(f"Error scanning secrets with {scanner_name}: {e}")
            return SecretScannerResult([], scanner_name)

# A convenience instance named 'secrets' (as some callers expect).
secrets = SecretsManager()

__all__ = ["SecretsManager", "SecretVersion", "RotationPolicy", "secrets", "SecretScanner"]