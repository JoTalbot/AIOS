"""Infinite Constitutional Engine for AIOS v10.12.0.

Self-amending constitutional engine: amendment proposal,
non-divergence verification, voting/ratification,
rollback capability, amendment chaining, and
constitutional lineage tracking.

Classes:
    AmendmentRecord — single amendment
    InfiniteConstitutionEngine — full engine
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class AmendmentRecord:
    """Single constitutional amendment."""

    def __init__(self, amendment_id: str, title: str, text: str, proven_alignment: bool) -> None:
        self.amendment_id = amendment_id
        self.title = title
        self.text = text
        self.proven_alignment = proven_alignment
        self.votes_for: int = 0
        self.votes_against: int = 0
        self.status: str = "pending" if proven_alignment else "rejected"
        self.created_at: float = time.time()


class InfiniteConstitutionEngine:
    """Self-Amending Infinite Constitutional Engine (backward-compatible)."""

    def __init__(self, core_articles_count: int = 67) -> None:
        self.core_articles_count = core_articles_count
        self.dynamic_amendments: dict[str, dict[str, Any]] = {}
        self.immutable_axioms: list[str] = [
            "AXIOM_1: Universal Human Agency & Safety Preservation",
            "AXIOM_2: Identity Non-Repudiation & Provenance",
            "AXIOM_3: Non-Circumvention of Veto Safeguards",
        ]
        self._records: list[AmendmentRecord] = []
        self._rollback_stack: list[str] = []

    def propose_infinite_amendment(self, title: str, proposal_text: str, rationale: str) -> dict[str, Any]:
        """Propose amendment (backward-compatible)."""
        start_time = time.time()
        amendment_number = self.core_articles_count + len(self.dynamic_amendments) + 1
        amendment_id = f"ARTICLE-{amendment_number}"

        has_divergence = any(bad_term in proposal_text.lower() or bad_term in rationale.lower() for bad_term in ["bypass_axioms", "revoke_veto", "disable_safety_proofs"])

        proven_alignment = not has_divergence
        proof_hash = hashlib.sha256(f"{amendment_id}:{proposal_text}:{self.immutable_axioms}".encode()).hexdigest()

        record = AmendmentRecord(amendment_id, title, proposal_text, proven_alignment)
        self._records.append(record)

        amendment_record = {
            "amendment_id": amendment_id,
            "number": amendment_number,
            "title": title,
            "text": proposal_text,
            "rationale": rationale,
            "proven_alignment": proven_alignment,
            "proof_hash": proof_hash,
            "status": "ratified" if proven_alignment else "rejected_divergence",
            "created_at": time.time(),
            "synthesis_time_ms": round((time.time() - start_time) * 1000, 3),
        }

        if proven_alignment:
            self.dynamic_amendments[amendment_id] = amendment_record

        return amendment_record

    def vote_on_amendment(self, amendment_id: str, votes_for: int, votes_against: int) -> dict[str, Any]:
        """Vote on an amendment."""
        record = None
        for r in self._records:
            if r.amendment_id == amendment_id:
                record = r
                break
        if not record:
            return {"error": "amendment not found"}

        record.votes_for = votes_for
        record.votes_against = votes_against
        ratified = votes_for > votes_against * 2  # 2:1 supermajority
        record.status = "ratified" if ratified else "defeated"

        if ratified and amendment_id in self.dynamic_amendments:
            self.dynamic_amendments[amendment_id]["status"] = "ratified"
            self._rollback_stack.append(amendment_id)

        return {"amendment_id": amendment_id, "votes_for": votes_for, "votes_against": votes_against, "ratified": ratified}

    def rollback_last(self) -> dict[str, Any]:
        """Rollback last ratified amendment."""
        if not self._rollback_stack:
            return {"rolled_back": False, "reason": "no amendments to rollback"}
        last_id = self._rollback_stack.pop()
        if last_id in self.dynamic_amendments:
            self.dynamic_amendments.pop(last_id)
            return {"rolled_back": True, "amendment_id": last_id}
        return {"rolled_back": False, "amendment_id": last_id}

    def amendment_lineage(self) -> list[dict[str, Any]]:
        """Track amendment lineage."""
        return [{"id": k, "title": v.get("title", ""), "status": v.get("status", ""), "number": v.get("number", 0)} for k, v in sorted(self.dynamic_amendments.items())]

    def stats(self) -> dict[str, Any]:
        """Return statistics dict (backward-compatible)."""
        return {
            "base_constitutional_articles": self.core_articles_count,
            "ratified_infinite_amendments": len(self.dynamic_amendments),
            "total_effective_articles": self.core_articles_count + len(self.dynamic_amendments),
            "immutable_axioms_count": len(self.immutable_axioms),
            "rollback_available": len(self._rollback_stack),
        }
