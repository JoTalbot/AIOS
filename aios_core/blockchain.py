"""Blockchain / Distributed Ledger for AIOS v10.12.0.

Blockchain: block creation with SHA-256 hashing, chain
validation, proof of work mining, smart contracts,
transaction tracking, and chain analytics.

Classes:
    Block           — single blockchain block
    Transaction     — blockchain transaction
    Blockchain      — full blockchain engine
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class Block:
    """Single blockchain block (backward-compatible)."""

    def __init__(self, index: int, data: dict[str, Any], previous_hash: str) -> None:
        self.index = index
        self.timestamp: float = time.time()
        self.data = data
        self.previous_hash = previous_hash
        self.nonce: int = 0
        self.hash: str = self.calculate_hash()

    def calculate_hash(self) -> str:
        """Calculate hash (backward-compatible)."""
        block_string = (
            f"{self.index}{self.timestamp}{self.data}{self.previous_hash}{self.nonce}"
        )
        return hashlib.sha256(block_string.encode()).hexdigest()


class Transaction:
    """Blockchain transaction."""

    def __init__(
        self, sender: str, receiver: str, amount: float, tx_type: str = "transfer"
    ) -> None:
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.tx_type = tx_type
        self.timestamp: float = time.time()
        self.tx_hash: str = hashlib.sha256(
            f"{sender}{receiver}{amount}{self.timestamp}".encode()
        ).hexdigest()


class SmartContract:
    """Simple smart contract simulation."""

    def __init__(
        self,
        contract_id: str,
        logic: str = "",
        conditions: dict[str, Any] | None = None,
    ) -> None:
        self.contract_id = contract_id
        self.logic = logic
        self.conditions = conditions or {}
        self.executed: int = 0

    def execute(self, transaction: Transaction) -> bool:
        """Execute contract conditions."""
        self.executed += 1
        # Check conditions
        if (
            self.conditions.get("min_amount")
            and transaction.amount < self.conditions["min_amount"]
        ):
            return False
        return True


class Blockchain:
    """Simple blockchain for audit and provenance (backward-compatible)."""

    def __init__(self, difficulty: int = 2) -> None:
        self.chain: list[Block] = []
        self._difficulty: int = difficulty
        self._pending_transactions: list[Transaction] = []
        self._contracts: dict[str, SmartContract] = {}
        self.create_genesis_block()

    def create_genesis_block(self) -> None:
        """Create genesis block (backward-compatible)."""
        genesis = Block(0, {"message": "Genesis Block"}, "0")
        self.chain.append(genesis)

    def add_block(self, data: dict[str, Any]) -> None:
        """Add block (backward-compatible)."""
        previous = self.chain[-1]
        new_block = Block(len(self.chain), data, previous.hash)
        self.mine_block(new_block)
        self.chain.append(new_block)

    def mine_block(self, block: Block) -> None:
        """Proof of work mining."""
        target = "0" * self._difficulty
        while block.hash[: self._difficulty] != target:
            block.nonce += 1
            block.hash = block.calculate_hash()

    def is_valid(self) -> bool:
        """Validate chain (backward-compatible)."""
        for i in range(1, len(self.chain)):
            if self.chain[i].previous_hash != self.chain[i - 1].hash:
                return False
            if self.chain[i].hash != self.chain[i].calculate_hash():
                return False
        return True

    def add_transaction(
        self, sender: str, receiver: str, amount: float, tx_type: str = "transfer"
    ) -> Transaction:
        """Add a pending transaction."""
        tx = Transaction(sender, receiver, amount, tx_type)
        self._pending_transactions.append(tx)
        return tx

    def register_contract(
        self,
        contract_id: str,
        logic: str = "",
        conditions: dict[str, Any] | None = None,
    ) -> SmartContract:
        """Register a smart contract."""
        contract = SmartContract(contract_id, logic, conditions)
        self._contracts[contract_id] = contract
        return contract

    def chain_analytics(self) -> dict[str, Any]:
        """Analyze chain statistics."""
        if not self.chain:
            return {"blocks": 0}
        return {
            "blocks": len(self.chain),
            "total_transactions": sum(
                len(b.data) if isinstance(b.data, list) else 1 for b in self.chain
            ),
            "avg_block_time": round(
                (self.chain[-1].timestamp - self.chain[0].timestamp)
                / max(len(self.chain) - 1, 1),
                2,
            ),
            "chain_hash": self.chain[-1].hash[:16],
        }

    def stats(self) -> dict[str, Any]:
        """Return statistics dict (backward-compatible)."""
        return {
            "blocks": len(self.chain),
            "valid": self.is_valid(),
            "difficulty": self._difficulty,
            "contracts": len(self._contracts),
        }
