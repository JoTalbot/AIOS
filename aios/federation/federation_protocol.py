"""AIOS Federation protocol definitions."""

from dataclasses import dataclass


@dataclass
class FederationMessage:
    source: str
    target: str
    action: str
    payload: dict


class FederationProtocol:
    def create_message(self, source: str, target: str, action: str, payload=None):
        return FederationMessage(
            source=source,
            target=target,
            action=action,
            payload=payload or {},
        )
