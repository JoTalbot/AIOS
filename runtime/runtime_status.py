"""Runtime status model."""

from dataclasses import dataclass

@dataclass
class RuntimeStatus:
    running: bool = False
    healthy: bool = True
