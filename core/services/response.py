"""AIOS service response model foundation."""

from dataclasses import dataclass
from typing import Any


@dataclass
class ServiceResponse:
    success: bool
    result: Any = None
    error: str | None = None
