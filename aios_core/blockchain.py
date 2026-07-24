"""Blockchain / Distributed Ledger for AIOS"""

import hashlib
import time
from typing import Dict, List


class Block:
    """Block."""
    def __init__(self, index: int, data: Dict, previous_hash: str):
        """Initialize Block."""
        self.index = index
        self.timestamp = time.time()
        self.data = data
        self.previous_hash = previous_hash
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        """Execute calculate hash."""
        block_string = f"{self.index}{self.timestamp}{self.data}{self.previous_hash}"
        return hashlib.sha256(block_string.encode()).hexdigest()


class Blockchain:
    """Simple blockchain for audit and provenance."""

    def __init__(self):
        """Initialize Blockchain."""
        self.chain: List[Block] = []
        self.create_genesis_block()

    def create_genesis_block(self) -> None:
        """Execute create genesis block."""
        genesis = Block(0, {"message": "Genesis Block"}, "0")
        self.chain.append(genesis)

    def add_block(self, data: Dict) -> None:
        """Execute add block."""
        previous = self.chain[-1]
        new_block = Block(len(self.chain), data, previous.hash)
        self.chain.append(new_block)

    def is_valid(self) -> bool:
        """Execute is valid."""
        for i in range(1, len(self.chain)):
            if self.chain[i].previous_hash != self.chain[i - 1].hash:
                return False
        return True

    def stats(self) -> dict:
        """Return statistics dict."""
        return {"blocks": len(self.chain), "valid": self.is_valid()}
