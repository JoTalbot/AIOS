"""AIOS Constitution Evolver v4.0.0-alpha

Self-evolving constitution system.
Allows the system to propose new articles and amendments based on runtime experience.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .storage import Database


@dataclass
class ProposedArticle:
    """A proposed new constitutional article."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = ""
    principle: str = ""
    laws: list[str] = field(default_factory=list)
    justification: str = ""
    confidence: float = 0.0
    status: str = "proposed"  # proposed, reviewed, accepted, rejected
    proposed_by: str = "system"
    created_at: str = ""


class ConstitutionEvolver:
    """Manages self-evolution of the AIOS Constitution."""

    def __init__(self, db: Optional[Database] = None):
        """Initialize ConstitutionEvolver."""
        self.db = db
        self._proposals: Dict[str, ProposedArticle] = {}
        self.version = "4.0.0-alpha"
        self._ensure_table()

    def _ensure_table(self) -> None:
        if self.db is None:
            return
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS constitution_proposals (
                id TEXT PRIMARY KEY,
                title TEXT,
                principle TEXT,
                laws TEXT,
                justification TEXT,
                confidence REAL,
                status TEXT,
                proposed_by TEXT,
                created_at TEXT
            )
        """
        )

    def propose_article(
        self,
        title: str,
        principle: str,
        laws: list[str],
        justification: str = "",
        confidence: float = 0.75,
    ) -> ProposedArticle:
        """Propose a new article for the constitution."""
        article = ProposedArticle(
            title=title,
            principle=principle,
            laws=laws,
            justification=justification,
            confidence=confidence,
            status="proposed",
        )
        self._proposals[article.id] = article

        if self.db:
            import json

            self.db.execute(
                """INSERT INTO constitution_proposals
                   (id, title, principle, laws, justification, confidence, status, proposed_by, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                (
                    article.id,
                    title,
                    principle,
                    json.dumps(laws),
                    justification,
                    confidence,
                    "proposed",
                    "system",
                ),
            )

        return article

    def review_proposal(self, proposal_id: str, decision: str, reviewer: str = "system") -> dict:
        """Review and accept/reject a proposal."""
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            return {"success": False, "error": "Proposal not found"}

        if decision.lower() in ("accept", "approved"):
            proposal.status = "accepted"
        elif decision.lower() in ("reject", "denied"):
            proposal.status = "rejected"
        else:
            proposal.status = "reviewed"

        return {
            "success": True,
            "proposal_id": proposal_id,
            "new_status": proposal.status,
            "reviewer": reviewer,
        }

    def generate_article_from_experience(self, experience: dict) -> Optional[ProposedArticle]:
        """Automatically generate an article proposal from observed patterns."""
        # Simple heuristic-based generation (placeholder for real ML)
        if "repeated_failure" in experience:
            return self.propose_article(
                title="ARTICLE-LXVIII — FAILURE RECOVERY",
                principle="The system must learn from repeated failures and implement safeguards.",
                laws=[
                    "All failures above threshold must trigger review.",
                    "Repeated failure patterns must be recorded in knowledge graph.",
                    "Recovery procedures must be proposed within 24 hours.",
                ],
                justification="Based on observed repeated failures in execution logs.",
                confidence=0.82,
            )
        return None

    def list_proposals(self, status: str | None = None) -> List[ProposedArticle]:
        """Execute list proposals."""
        if status:
            return [p for p in self._proposals.values() if p.status == status]
        return list(self._proposals.values())

    def stats(self) -> dict:
        """Return statistics dict."""
        return {
            "version": self.version,
            "total_proposals": len(self._proposals),
            "by_status": {
                status: len([p for p in self._proposals.values() if p.status == status])
                for status in ["proposed", "accepted", "rejected", "reviewed"]
            },
        }
