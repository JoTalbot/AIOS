"""AIOS service request model foundation."""

from dataclasses import dataclass
from typing import Any


@dataclass
class ServiceRequest:
    intent: str
    payload: dict[str, Any]
    requester: str | None = None
