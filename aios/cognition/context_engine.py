"""Context composition layer for cognitive processing."""

from dataclasses import dataclass, field


@dataclass
class ContextEngine:
    context: dict[str, object] = field(default_factory=dict)

    def set(self, key: str, value: object):
        self.context[key] = value

    def get(self, key: str, default=None):
        return self.context.get(key, default)
