"""Validation helpers for Digital Twin lifecycle readiness."""

from typing import Iterable


REQUIRED_COMPONENTS = {
    "simulation",
    "prediction",
    "sync",
    "health",
    "audit",
}


def validate_components(components: Iterable[str]) -> bool:
    return REQUIRED_COMPONENTS.issubset(set(components))
