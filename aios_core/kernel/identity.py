"""Agent identities and their in-memory validation registry."""

from __future__ import annotations

from dataclasses import dataclass, field

from .exceptions import UnknownIdentity


@dataclass(frozen=True)
class AgentIdentity:
    """Authenticated identity attributes used by kernel policy evaluation."""

    agent_id: str
    role: str
    capabilities: frozenset[str] = field(default_factory=frozenset)

    def __init__(self, agent_id: str, role: str, capabilities=None):
        object.__setattr__(self, "agent_id", agent_id)
        object.__setattr__(self, "role", role)
        object.__setattr__(self, "capabilities", frozenset(capabilities or ()))

    def has_capability(self, capability: str) -> bool:
        """Return whether this identity declares *capability*."""
        return capability in self.capabilities


class IdentityRegistry:
    """Fail-closed registry for identities known to the kernel."""

    def __init__(self, identities: tuple[AgentIdentity, ...] = ()) -> None:
        self._identities = {identity.agent_id: identity for identity in identities}

    def register(self, identity: AgentIdentity) -> None:
        """Register or replace an identity by its stable identifier."""
        self._identities[identity.agent_id] = identity

    def validate(self, agent_id: str) -> AgentIdentity:
        """Return a known identity or reject an unregistered caller."""
        try:
            return self._identities[agent_id]
        except KeyError as exc:
            raise UnknownIdentity(f"unknown agent identity: {agent_id}") from exc
