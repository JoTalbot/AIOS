"""Canonical composition root for the AIOS v20 architecture."""

from .approval import ApprovalGate, ApprovalRequest, ApprovalStatus
from .audit import ArchitectureAuditStore
from .delegation import DelegationGrant, DelegationRegistry
from .runtime import ArchitectureRuntime
from .supervisor_adapter import SpecialistInvocation, SupervisedRun, SupervisorRuntimeExecutor

__all__ = [
    "ApprovalGate",
    "ApprovalRequest",
    "ApprovalStatus",
    "ArchitectureAuditStore",
    "ArchitectureRuntime",
    "DelegationGrant",
    "DelegationRegistry",
    "SpecialistInvocation",
    "SupervisedRun",
    "SupervisorRuntimeExecutor",
]
