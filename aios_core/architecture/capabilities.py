"""Explicit capability ownership and risk metadata registry."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CapabilityDefinition:
    name: str
    owner: str
    risk: str = "normal"
    enabled: bool = True


class CapabilityRegistry:
    def __init__(self, definitions: tuple[CapabilityDefinition, ...] = ()) -> None:
        self.definitions = {item.name: item for item in definitions}

    def register(self, definition: CapabilityDefinition) -> None:
        if definition.name in self.definitions:
            raise ValueError(f"capability already registered: {definition.name}")
        if definition.risk not in {"low", "normal", "high", "critical"}:
            raise ValueError(f"unknown capability risk: {definition.risk}")
        self.definitions[definition.name] = definition

    def require(self, name: str) -> CapabilityDefinition:
        try:
            definition = self.definitions[name]
        except KeyError as exc:
            raise RuntimeError("capability is not registered") from exc
        if not definition.enabled:
            raise RuntimeError("capability is disabled")
        return definition
