"""AIOS REST API v1.0.0

HTTP/REST API layer for AIOS. Built on Starlette.
Provides RESTful access to all AIOS subsystems.
"""

from .app import create_app, AIOSAPI

__all__ = ["create_app", "AIOSAPI"]