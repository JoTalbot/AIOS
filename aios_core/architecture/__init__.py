"""Canonical composition root for the AIOS v20 architecture."""

from .approval import ApprovalGate, ApprovalRequest, ApprovalStatus
from .audit import ArchitectureAuditStore
from .runtime import ArchitectureRuntime

__all__ = [
    "ApprovalGate",
    "ApprovalRequest",
    "ApprovalStatus",
    "ArchitectureAuditStore",
    "ArchitectureRuntime",
]
