"""Federated state synchronization primitives."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class StateUpdate:
    key: str
    value: object


class StateSync:
    def __init__(self):
        self.state: Dict[str, object] = {}

    def apply(self, update: StateUpdate):
        self.state[update.key] = update.value

    def snapshot(self):
        return dict(self.state)
