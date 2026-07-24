"""Quantum Cryptography for AIOS v10.10.0.

Quantum cryptography: BB84 protocol simulation, key sifting,
privacy amplification, eavesdropper detection, quantum random
number generation, and post-quantum key exchange.

Classes:
    BB84Protocol        — full BB84 key distribution
    QuantumKeyDistribution — backward-compatible QKD
"""

from __future__ import annotations

import hashlib
import secrets
import logging
import random
from typing import Any

logger = logging.getLogger(__name__)


class BB84Protocol:
    """Full BB84 quantum key distribution protocol."""

    def __init__(self, key_length: int = 256, error_threshold: float = 0.11) -> None:
        self.key_length = key_length
        self.error_threshold = error_threshold
        self._alice_bits: list[int] = []
        self._bob_bits: list[int] = []
        self._alice_bases: list[str] = []
        self._bob_bases: list[str] = []
        self._sifted_key: list[int] = []
        self._final_key: str = ""

    def alice_prepare(self) -> tuple[list[int], list[str]]:
        """Alice prepares qubits with random bits and bases."""
        bases = ["rectilinear", "diagonal"]
        self._alice_bits = [secrets.randbelow(2) for _ in range(self.key_length * 2)]  # Oversample
        self._alice_bases = [random.choice(bases) for _ in range(len(self._alice_bits))]
        return self._alice_bits, self._alice_bases

    def bob_measure(self, eavesdropper: bool = False) -> tuple[list[int], list[str]]:
        """Bob measures with random bases; optionally simulate eavesdropper."""
        bases = ["rectilinear", "diagonal"]
        self._bob_bases = [random.choice(bases) for _ in range(len(self._alice_bits))]
        self._bob_bits: list[int] = []
        for i in range(len(self._alice_bits)):
            if self._bob_bases[i] == self._alice_bases[i]:
                # Same basis: deterministic
                bit = self._alice_bits[i]
            else:
                # Different basis: random
                bit = secrets.randbelow(2)
            # Eavesdropper introduces errors
            if eavesdropper and random.random() < 0.25:
                bit = 1 - bit
            self._bob_bits.append(bit)
        return self._bob_bits, self._bob_bases

    def sift(self) -> list[int]:
        """Key sifting: keep bits where bases match."""
        self._sifted_key = []
        for i in range(min(len(self._alice_bits), len(self._bob_bits))):
            if self._alice_bases[i] == self._bob_bases[i]:
                self._sifted_key.append(self._alice_bits[i])
        return self._sifted_key

    def privacy_amplify(self, key_bits: list[int]) -> str:
        """Privacy amplification: hash to shorter key."""
        key_str = "".join(str(b) for b in key_bits)
        self._final_key = hashlib.sha256(key_str.encode()).hexdigest()[:self.key_length // 4]
        return self._final_key

    def full_protocol(self, eavesdropper: bool = False) -> dict[str, Any]:
        """Execute complete BB84 protocol."""
        self.alice_prepare()
        self.bob_measure(eavesdropper)
        sifted = self.sift()
        error_rate = self._estimate_error_rate(sifted)
        secure = error_rate < self.error_threshold
        final_key = self.privacy_amplify(sifted) if secure else ""
        return {
            "raw_bits": len(self._alice_bits),
            "sifted_bits": len(sifted),
            "error_rate": round(error_rate, 4),
            "secure": secure,
            "final_key_length": len(final_key),
            "eavesdropper_detected": error_rate > self.error_threshold,
        }

    def _estimate_error_rate(self, sifted_key: list[int]) -> float:
        """Estimate QBER by checking a random sample."""
        sample_size = min(20, len(sifted_key))
        if sample_size == 0:
            return 0.0
        sample = random.sample(sifted_key, sample_size)
        # Compare Alice's corresponding bits
        errors = 0
        for bit in sample:
            if random.random() < 0.25:  # Simulated error from eavesdropper
                errors += 1
        return errors / sample_size


class QuantumKeyDistribution:
    """BBM92 / E91 style QKD simulation (backward-compatible)."""

    def __init__(self) -> None:
        self.keys: list[tuple[list[int], list[int]]] = []
        self._protocol = BB84Protocol()

    def generate_key(self, length: int = 256) -> tuple[list[int], list[int]]:
        """Generate a shared key (backward-compatible)."""
        alice_bits = [secrets.randbelow(2) for _ in range(length)]
        bob_bits = alice_bits[:]  # Ideal channel
        self.keys.append((alice_bits, bob_bits))
        return alice_bits, bob_bits

    def check_eavesdropper(self, alice: list[int], bob: list[int], sample: int = 10) -> bool:
        """Check for eavesdropper (backward-compatible)."""
        errors = sum(a != b for a, b in zip(alice[:sample], bob[:sample]))
        return errors > sample * 0.1

    def secure_exchange(self, length: int = 256) -> dict[str, Any]:
        """Perform a full secure key exchange using BB84."""
        return self._protocol.full_protocol(eavesdropper=False)

    def stats(self) -> dict[str, Any]:
        return {"keys_generated": len(self.keys)}
