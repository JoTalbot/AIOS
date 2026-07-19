"""AIOS Evolution Manager v3.0.0

Controls safe lifecycle of AIOS modifications through a 7-stage pipeline:
proposal -> testing -> sandbox -> simulation -> audit -> approval -> deployment

Persists to evolution_records table in SQLite.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .storage import Database

# The 7 evolution stages
_EVOLUTION_STAGES = [
    "proposal",
    "testing",
    "sandbox",
    "simulation",
    "audit",
    "approval",
    "deployment",
]


class EvolutionManager:
    """Manages controlled evolution of AIOS system.

    v3.0.0: Full 7-stage pipeline with SQLite persistence.
    """

    def __init__(self, db: Optional[Database] = None, version: str = "3.0.0"):
        self.version = version
        self.db = db
        self.stages = list(_EVOLUTION_STAGES)

    def propose(
        self,
        change: dict,
        component: str = "",
        reason: str = "",
    ) -> dict:
        """Create a new evolution proposal.

        Args:
            change: The proposed change description.
            component: Target component (e.g., "reasoning_engine").
            reason: Reason for the change.

        Returns:
            The proposal dict with id and stage info.
        """
        proposal_id = self.db.new_id() if self.db else "no-db"
        now = datetime.now(timezone.utc).isoformat()

        proposal = {
            "id": proposal_id,
            "change": change,
            "component": component,
            "reason": reason,
            "stage": "proposal",
            "stage_index": 0,
            "status": "proposed",
            "proposed_at": now,
            "completed_at": None,
            "stages": list(self.stages),
        }

        if self.db:
            self.db.execute(
                """INSERT INTO evolution_records
                   (id, evolution_type, previous_state, new_state, reason,
                    stage, status, proposed_at, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    proposal_id,
                    "self_modification",
                    None,
                    self.db.to_json(change),
                    reason,
                    "proposal",
                    "proposed",
                    now,
                    self.db.to_json({
                        "component": component,
                        "stage_index": 0,
                    }),
                ),
            )

        return proposal

    def advance(self, proposal_id: str) -> dict:
        """Advance a proposal to the next stage.

        Args:
            proposal_id: The proposal to advance.

        Returns:
            Updated proposal dict, or raises ValueError if not found.
        """
        proposal = self.get_proposal(proposal_id)
        if proposal is None:
            raise ValueError(f"Proposal not found: {proposal_id}")

        if proposal.get("status") in {"rejected", "deploying"}:
            raise ValueError(f"Cannot advance proposal in terminal state: {proposal['status']}")

        current_index = proposal["stage_index"]
        if current_index >= len(self.stages) - 1:
            raise ValueError("Proposal is already at final stage")
        if proposal.get("stage") == "approval" and proposal.get("status") != "approved":
            raise ValueError("An approval-stage proposal must be approved before deployment")

        next_index = current_index + 1
        next_stage = self.stages[next_index]

        # Determine status
        if next_stage == "deployment":
            new_status = "deploying"
        elif next_stage == "approval":
            new_status = "pending_approval"
        else:
            new_status = f"in_{next_stage}"

        if self.db:
            self.db.execute(
                """UPDATE evolution_records
                   SET stage = ?, status = ?, metadata = ?
                   WHERE id = ?""",
                (
                    next_stage,
                    new_status,
                    self.db.to_json({
                        "component": proposal.get("component", ""),
                        "stage_index": next_index,
                    }),
                    proposal_id,
                ),
            )

        proposal["stage"] = next_stage
        proposal["stage_index"] = next_index
        proposal["status"] = new_status

        return proposal

    def approve(self, proposal_id: str) -> dict:
        """Approve a proposal (marks it as approved).

        Args:
            proposal_id: The proposal to approve.

        Returns:
            Updated proposal dict.
        """
        proposal = self.get_proposal(proposal_id)
        if proposal is None:
            raise ValueError(f"Proposal not found: {proposal_id}")

        if proposal.get("stage") != "approval" or proposal.get("status") != "pending_approval":
            raise ValueError("Only proposals pending at the approval stage can be approved")

        if self.db:
            self.db.execute(
                """UPDATE evolution_records
                   SET status = 'approved', completed_at = ?
                   WHERE id = ?""",
                (datetime.now(timezone.utc).isoformat(), proposal_id),
            )

        proposal["status"] = "approved"
        proposal["completed_at"] = datetime.now(timezone.utc).isoformat()
        return proposal

    def reject(self, proposal_id: str, reason: str = "") -> dict:
        """Reject a proposal.

        Args:
            proposal_id: The proposal to reject.
            reason: Reason for rejection.

        Returns:
            Updated proposal dict.
        """
        proposal = self.get_proposal(proposal_id)
        if proposal is None:
            raise ValueError(f"Proposal not found: {proposal_id}")
        if proposal.get("status") in {"approved", "rejected", "deploying"}:
            raise ValueError(f"Cannot reject proposal in terminal state: {proposal['status']}")

        if self.db:
            self.db.execute(
                """UPDATE evolution_records
                   SET status = 'rejected', completed_at = ?
                   WHERE id = ?""",
                (datetime.now(timezone.utc).isoformat(), proposal_id),
            )

        proposal["status"] = "rejected"
        proposal["rejection_reason"] = reason
        proposal["completed_at"] = datetime.now(timezone.utc).isoformat()
        return proposal

    def get_proposal(self, proposal_id: str) -> Optional[dict]:
        """Get a proposal by ID.

        Returns:
            Proposal dict or None if not found.
        """
        if self.db:
            row = self.db.query_one(
                "SELECT * FROM evolution_records WHERE id = ?",
                (proposal_id,),
            )
            if row is None:
                return None
            return self._row_to_dict(row)
        return None

    def list_proposals(self, status: Optional[str] = None) -> list[dict]:
        """List all proposals, optionally filtered by status.

        Args:
            status: Filter by status string.

        Returns:
            List of proposal dicts.
        """
        if self.db is None:
            return []

        if status:
            rows = self.db.query(
                "SELECT * FROM evolution_records WHERE status = ? "
                "ORDER BY proposed_at DESC",
                (status,),
            )
        else:
            rows = self.db.query(
                "SELECT * FROM evolution_records ORDER BY proposed_at DESC"
            )

        return [self._row_to_dict(r) for r in rows]

    def can_deploy(self, proposal_id: str) -> bool:
        """Check if a proposal can be deployed.

        A proposal can be deployed if:
        - It exists
        - Its stage is at least 'approval'
        - Its status is 'approved' or 'pending_approval'

        Args:
            proposal_id: The proposal to check.

        Returns:
            True if deployment is permitted.
        """
        proposal = self.get_proposal(proposal_id)
        if proposal is None:
            return False

        # Must be at the approval or deployment stage
        stage_index = proposal.get("stage_index", 0)
        if stage_index < 5:  # Must have passed audit (index 4)
            return False

        status = proposal.get("status", "")
        return status in ("approved", "pending_approval")

    def _row_to_dict(self, row: dict) -> dict:
        """Convert a DB row to a proposal dict."""
        metadata = {}
        if row.get("metadata"):
            try:
                from .storage import Database as DB
                metadata = DB.from_json(row["metadata"])
            except Exception:
                metadata = {}

        new_state = row.get("new_state")
        change = {}
        if new_state:
            try:
                from .storage import Database as DB
                change = DB.from_json(new_state)
            except Exception:
                change = {}

        return {
            "id": row["id"],
            "change": change,
            "component": metadata.get("component", ""),
            "reason": row.get("reason", ""),
            "stage": row.get("stage", "proposal"),
            "stage_index": metadata.get("stage_index", 0),
            "status": row.get("status", "unknown"),
            "proposed_at": row.get("proposed_at"),
            "completed_at": row.get("completed_at"),
            "stages": list(self.stages),
        }

    def stats(self) -> dict:
        """Return evolution manager statistics."""
        if self.db is None:
            return {
                "version": self.version,
                "total_proposals": 0,
                "by_status": {},
                "stages": self.stages,
                "storage": "none",
            }

        rows = self.db.query(
            "SELECT status, COUNT(*) as cnt FROM evolution_records GROUP BY status"
        )
        by_status = {r["status"]: r["cnt"] for r in rows}

        total = self.db.query_one(
            "SELECT COUNT(*) as cnt FROM evolution_records"
        )

        return {
            "version": self.version,
            "total_proposals": total["cnt"] if total else 0,
            "by_status": by_status,
            "stages": self.stages,
            "storage": "sqlite",
        }
