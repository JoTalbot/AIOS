"""Validate delegation chains as monotonically narrowing authority."""

from __future__ import annotations

from itertools import pairwise

from .delegation import DelegationGrant


class DelegationChainValidator:
    def validate(self, chain: tuple[DelegationGrant, ...]) -> None:
        if not chain:
            raise RuntimeError("delegation chain is empty")
        for parent, child in pairwise(chain):
            if child.owner_id != parent.owner_id:
                raise RuntimeError("delegation owner changed")
            if child.delegated_by != parent.agent_id:
                raise RuntimeError("delegation lineage broken")
            if child.task_id != parent.task_id:
                raise RuntimeError("delegation task changed")
            if not child.capabilities <= parent.capabilities:
                raise RuntimeError("delegation scope expanded")
            if child.expires_at > parent.expires_at:
                raise RuntimeError("delegation lifetime expanded")
