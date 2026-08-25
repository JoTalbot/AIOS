"""Policy decision point for AIOS v20 action requests."""

from __future__ import annotations

from .audit import AuditLogger
from .context import ExecutionContext
from .decisions import PolicyDecision
from .identity import IdentityRegistry
from .policies import PolicyEngine
from .trust import TrustManager


class Kernel:
    """Validate identity, evaluate current trust and audit every policy decision."""

    def __init__(
        self,
        identity: IdentityRegistry,
        trust: TrustManager,
        policy: PolicyEngine,
        audit: AuditLogger,
    ) -> None:
        self.identity = identity
        self.trust = trust
        self.policy = policy
        self.audit = audit

    def process(self, context: ExecutionContext) -> PolicyDecision:
        """Evaluate one request through the identity → trust → policy → audit chain."""
        identity = self.identity.validate(context.agent_id)
        trust_level = self.trust.evaluate(context.agent_id)
        decision = self.policy.evaluate(context.action, trust_level, identity)
        self.audit.record(decision)
        return decision
