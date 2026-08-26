"""Unified runtime error response model."""

from dataclasses import dataclass


@dataclass
class ErrorResponse:
    code: str
    message: str
