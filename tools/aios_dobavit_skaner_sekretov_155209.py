import os
import subprocess
from dataclasses import dataclass
from typing import List

__all__ = ['scan_secrets', 'audit_llm_keys']

@dataclass
class ScanResult:
    """Result of secrets scan"""
    secrets_found: bool
    log_messages: List[str]

def scan_secrets(target_path: str) -> ScanResult:
    """
    Scan secrets using truffleHog.

    Args:
    target_path (str): Path to scan for secrets.

    Returns:
    ScanResult: Result of secrets scan.
    """
    try:
        output = subprocess.check_output(['truffleHog', target_path]).decode('utf-8')
        log_messages = output.splitlines()
        secrets_found = any('secret' in line.lower() for line in log_messages)
        return ScanResult(secrets_found, log_messages)
    except subprocess.CalledProcessError as e:
        return ScanResult(False, [f"Error scanning secrets: {e}"])
    except Exception as e:
        return ScanResult(False, [f"Error scanning secrets: {e}"])

def audit_llm_keys(log_path: str, config_path: str) -> List[str]:
    """
    Audit LLM keys by checking logs and configurations.

    Args:
    log_path (str): Path to logs.
    config_path (str): Path to configurations.

    Returns:
    List[str]: List of audit messages.
    """
    try:
        log_messages = []
        with open(log_path, 'r') as f:
            log_messages = f.readlines()
        config_messages = []
        with open(config_path, 'r') as f:
            config_messages = f.readlines()
        audit_messages = []
        for line in log_messages:
            if 'key' in line.lower():
                audit_messages.append(f"Potential LLM key found in log: {line.strip()}")
        for line in config_messages:
            if 'key' in line.lower():
                audit_messages.append(f"Potential LLM key found in config: {line.strip()}")
        return audit_messages
    except Exception as e:
        return [f"Error auditing LLM keys: {e}"]

if __name__ == '__main__':
    target_path = 'path/to/scan'
    scan_result = scan_secrets(target_path)
    print(f"Secrets found: {scan_result.secrets_found}")
    for message in scan_result.log_messages:
        print(message)
    log_path = 'path/to/logs'
    config_path = 'path/to/config'
    audit_messages = audit_llm_keys(log_path, config_path)
    for message in audit_messages:
        print(message)