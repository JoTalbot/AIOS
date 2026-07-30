"""
Module for checking system health metrics on Linux systems.
Reads from /proc filesystem to get uptime and memory information.
"""

import time
from dataclasses import dataclass
from typing import Dict, Optional

__all__ = ['health_check', 'SystemHealth']


@dataclass
class SystemHealth:
    """Dataclass representing system health metrics."""
    status: str
    uptime_seconds: float
    memory_mb: float


def _read_proc_file(filepath: str) -> Optional[str]:
    """Helper function to read /proc files safely."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except (FileNotFoundError, PermissionError, OSError):
        return None


def _parse_uptime() -> Optional[float]:
    """Parse system uptime from /proc/uptime."""
    content = _read_proc_file('/proc/uptime')
    if content is None:
        return None

    try:
        uptime_str = content.split()[0]
        return float(uptime_str)
    except (ValueError, IndexError):
        return None


def _parse_memory() -> Optional[float]:
    """Parse available memory from /proc/meminfo."""
    content = _read_proc_file('/proc/meminfo')
    if content is None:
        return None

    try:
        for line in content.splitlines():
            if line.startswith('MemAvailable:'):
                parts = line.split()
                if len(parts) >= 2:
                    kb = int(parts[1])
                    return kb / 1024  # Convert KB to MB
        return None
    except (ValueError, IndexError):
        return None


def health_check() -> Dict[str, str | float]:
    """
    Perform a system health check.
    
    Returns:
        dict: Contains status ('OK' or 'ERROR'), uptime in seconds, 
              and available memory in MB.
    """
    uptime = _parse_uptime()
    memory = _parse_memory()

    if uptime is None or memory is None:
        status = 'ERROR'
    else:
        status = 'OK'

    return SystemHealth(
        status=status,
        uptime_seconds=uptime if uptime is not None else 0.0,
        memory_mb=memory if memory is not None else 0.0
    ).__dict__


if __name__ == '__main__':
    # Test the health check functionality
    print("Running system health check...")
    result = health_check()
    print(f"Status: {result['status']}")
    print(f"Uptime: {result['uptime_seconds']:.2f} seconds")
    print(f"Available memory: {result['memory_mb']:.2f} MB")