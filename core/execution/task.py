"""AIOS task model foundation."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Task:
    id: str
    input: Any
    metadata: dict = field(default_factory=dict)
