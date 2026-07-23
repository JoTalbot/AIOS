"""Quantum Cryptography for AIOS"""

import secrets
from typing import List, Tuple


class QuantumKeyDistribution:
    """BBM92 / E91 style QKD simulation."""

    def __init__(self):
        self.keys: List[Tuple] = []

    def generate_key(self, length: int = 256) -> Tuple[List[int], List[int]]:
        """Execute generate key."""
        alice_bits = [secrets.randbelow(2) for _ in range(length)]
        bob_bits = alice_bits[:]  # ideal channel
        self.keys.append((alice_bits, bob_bits))
        return alice_bits, bob_bits

    def check_eavesdropper(self, alice: List[int], bob: List[int], sample: int = 10) -> bool:
        """Execute check eavesdropper."""
        errors = sum(a != b for a, b in zip(alice[:sample], bob[:sample]))
        return errors > sample * 0.1  # >10% error = eavesdropper

    def stats(self) -> dict:
        """Return statistics dict."""
        return {"keys_generated": len(self.keys)}
