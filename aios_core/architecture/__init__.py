"""Canonical composition root for the AIOS v20 architecture."""

from .approval import ApprovalGate, ApprovalRequest, ApprovalStatus
from .approval_transport import ApprovalCommand, ApprovalCommandVerifier
from .audit import ArchitectureAuditStore
from .audit_tools import AuditQuery
from .capabilities import CapabilityDefinition, CapabilityRegistry
from .delegation import DelegationGrant, DelegationRegistry
from .delegation_chain import DelegationChainValidator
from .health import ArchitectureHealth, architecture_health
from .idempotency import IdempotencyLedger, IdempotencyRecord
from .risk import RiskControls, controls_for
from .runtime import ArchitectureRuntime
from .security_profile import ArchitectureSecurityProfile
from .signing import HMACSigner
from .supervisor_adapter import SpecialistInvocation, SupervisedRun, SupervisorRuntimeExecutor

__all__ = [
    "ApprovalCommand",
    "ApprovalCommandVerifier",
    "ApprovalGate",
    "ApprovalRequest",
    "ApprovalStatus",
    "ArchitectureAuditStore",
    "ArchitectureHealth",
    "ArchitectureRuntime",
    "ArchitectureSecurityProfile",
    "AuditQuery",
    "CapabilityDefinition",
    "CapabilityRegistry",
    "DelegationChainValidator",
    "DelegationGrant",
    "DelegationRegistry",
    "HMACSigner",
    "IdempotencyLedger",
    "IdempotencyRecord",
    "RiskControls",
    "SpecialistInvocation",
    "SupervisedRun",
    "SupervisorRuntimeExecutor",
    "architecture_health",
    "controls_for",
]
