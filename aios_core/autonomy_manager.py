"""AIOS Autonomy Manager v3.0.0

Article LXVII — Autonomy Level Management.

Manages agent autonomy levels from fully manual (LEVEL_0) to
self-directed (LEVEL_5), tracking performance records and
determining automatic approval eligibility based on risk levels.

Persists to autonomy_profiles table in SQLite.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import TYPE_CHECKING

__all__ = ["AutonomyLevel", "AgentAutonomyProfile", "AutonomyManager"]

if TYPE_CHECKING:
    from .storage import Database


class AutonomyLevel(IntEnum):
    """Agent autonomy levels, from fully manual to self-directed."""

    LEVEL_0_MANUAL = 0  # No autonomy, every action requires human approval
    LEVEL_1_ASSISTED = 1  # Suggests actions, human approves each
    LEVEL_2_SUPERVISED = 2  # Executes low-risk actions autonomously, human reviews
    LEVEL_3_MANAGED = 3  # Executes medium-risk autonomously, reports periodically
    LEVEL_4_AUTONOMOUS = 4  # Full autonomy for operational tasks, human for critical
    LEVEL_5_SELF_DIRECTED = 5  # Full self-direction within constitutional bounds


@dataclass
class AgentAutonomyProfile:
    """Autonomy profile for a single agent."""

    agent_id: str
    level: AutonomyLevel = AutonomyLevel.LEVEL_0_MANUAL
    granted_by: str = "system"
    granted_at: str = ""
    expires_at: str | None = None
    restrictions: dict = field(default_factory=dict)
    track_record: dict = field(
        default_factory=lambda: {
            "total_actions": 0,
            "successes": 0,
            "failures": 0,
            "reviews_triggered": 0,
        }
    )
    metadata: dict = field(default_factory=dict)


class AutonomyManager:
    """Manages agent autonomy levels and approval decisions.

    v3.0.0: Full autonomy lifecycle with SQLite persistence,
    risk-based approval gating, and promotion/demotion logic.
    """

    def __init__(self, db: Database | None = None):
        """Initialize AutonomyManager."""
        self.db = db
        self._profiles: dict[str, AgentAutonomyProfile] = {}

        if self.db:
            self.db.execute(
                """CREATE TABLE IF NOT EXISTS autonomy_profiles (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL UNIQUE,
                    level INTEGER NOT NULL DEFAULT 0,
                    granted_by TEXT,
                    granted_at TEXT NOT NULL,
                    expires_at TEXT,
                    restrictions TEXT,
                    track_record TEXT,
                    metadata TEXT
                )"""
            )
            self.db.execute(
                "CREATE INDEX IF NOT EXISTS idx_autonomy_agent ON autonomy_profiles(agent_id)"
            )
            self.db.execute(
                "CREATE INDEX IF NOT EXISTS idx_autonomy_level ON autonomy_profiles(level)"
            )
            self._load_profiles()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_profiles(self) -> None:
        """Load all existing profiles from the database into memory."""
        if self.db is None:
            return
        rows = self.db.query("SELECT * FROM autonomy_profiles")
        for row in rows:
            profile = self._row_to_profile(row)
            self._profiles[profile.agent_id] = profile

    def _profile_to_dict(self, profile: AgentAutonomyProfile) -> dict:
        """Convert an AgentAutonomyProfile to a plain dict."""
        return {
            "agent_id": profile.agent_id,
            "level": int(profile.level),
            "granted_by": profile.granted_by,
            "granted_at": profile.granted_at,
            "expires_at": profile.expires_at,
            "restrictions": profile.restrictions,
            "track_record": profile.track_record,
            "metadata": profile.metadata,
        }

    def _row_to_profile(self, row: dict) -> AgentAutonomyProfile:
        """Convert a database row to an AgentAutonomyProfile."""
        from .storage import Database as DB

        restrictions = {}
        if row.get("restrictions"):
            try:
                restrictions = DB.from_json(row["restrictions"])
            except Exception:
                restrictions = {}

        track_record = {
            "total_actions": 0,
            "successes": 0,
            "failures": 0,
            "reviews_triggered": 0,
        }
        if row.get("track_record"):
            try:
                track_record = DB.from_json(row["track_record"])
            except Exception:
                pass  # Corrupt track_record JSON — reset to defaults
        if row.get("metadata"):
            try:
                metadata = DB.from_json(row["metadata"])
            except Exception:
                pass  # Corrupt metadata JSON
                metadata = {}

        return AgentAutonomyProfile(
            agent_id=row["agent_id"],
            level=AutonomyLevel(row["level"]),
            granted_by=row.get("granted_by", "system"),
            granted_at=row.get("granted_at", ""),
            expires_at=row.get("expires_at"),
            restrictions=restrictions,
            track_record=track_record,
            metadata=metadata,
        )

    def _persist_profile(self, profile: AgentAutonomyProfile) -> None:
        """Upsert a profile into the database."""
        if self.db is None:
            return
        from .storage import Database as DB

        profile_id = profile.metadata.get("_db_id", profile.agent_id)
        self.db.execute(
            """INSERT INTO autonomy_profiles
               (id, agent_id, level, granted_by, granted_at, expires_at,
                restrictions, track_record, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(agent_id) DO UPDATE SET
                   level = excluded.level,
                   granted_by = excluded.granted_by,
                   granted_at = excluded.granted_at,
                   expires_at = excluded.expires_at,
                   restrictions = excluded.restrictions,
                   track_record = excluded.track_record,
                   metadata = excluded.metadata""",
            (
                profile_id,
                profile.agent_id,
                int(profile.level),
                profile.granted_by,
                profile.granted_at,
                profile.expires_at,
                DB.to_json(profile.restrictions),
                DB.to_json(profile.track_record),
                DB.to_json(profile.metadata),
            ),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def grant_autonomy(
        self,
        agent_id: str,
        level: int,
        granted_by: str = "system",
        expires_at: str | None = None,
        restrictions: dict | None = None,
    ) -> dict:
        """Grant or update autonomy level for an agent.

        Args:
            agent_id: The agent identifier.
            level: Autonomy level (0-5).
            granted_by: Who granted this autonomy.
            expires_at: Optional expiry ISO timestamp.
            restrictions: Optional extra restrictions dict.

        Returns:
            The profile dict for the agent.
        """
        from .storage import Database as DB

        now = DB.now_iso()
        profile = AgentAutonomyProfile(
            agent_id=agent_id,
            level=AutonomyLevel(level),
            granted_by=granted_by,
            granted_at=now,
            expires_at=expires_at,
            restrictions=restrictions or {},
            track_record={
                "total_actions": 0,
                "successes": 0,
                "failures": 0,
                "reviews_triggered": 0,
            },
            metadata={"_db_id": agent_id},
        )

        # Preserve existing track_record if upgrading
        existing = self._profiles.get(agent_id)
        if existing is not None:
            profile.track_record = existing.track_record
            profile.metadata = existing.metadata

        self._profiles[agent_id] = profile
        self._persist_profile(profile)
        return self._profile_to_dict(profile)

    def revoke_autonomy(self, agent_id: str, reason: str = "") -> dict:
        """Revoke autonomy for an agent (reset to LEVEL_0).

        Args:
            agent_id: The agent identifier.
            reason: Reason for revocation.

        Returns:
            The updated profile dict.
        """
        profile = self._profiles.get(agent_id)
        if profile is None:
            profile = AgentAutonomyProfile(
                agent_id=agent_id,
                granted_at=self.db.now_iso() if self.db else "",
                metadata={"_db_id": agent_id},
            )

        profile.level = AutonomyLevel.LEVEL_0_MANUAL
        profile.metadata["revocation_reason"] = reason

        self._profiles[agent_id] = profile
        self._persist_profile(profile)
        return self._profile_to_dict(profile)

    def check_autonomy(self, agent_id: str, action_risk: str = "low") -> dict:
        """Determine if an agent's action is auto-approved or needs human review.

        Risk-based approval matrix:
            - Level 0/1: ALWAYS needs approval
            - Level 2:   low auto, medium+ needs approval
            - Level 3:   low/medium auto, high+ needs approval
            - Level 4:   low/medium/high auto, critical needs approval
            - Level 5:   all risks auto-approved within constitutional bounds

        Args:
            agent_id: The agent identifier.
            action_risk: Risk level of the action ("low", "medium", "high", "critical").

        Returns:
            Dict with approval decision details.
        """
        profile = self._profiles.get(agent_id)
        if profile is None:
            level = AutonomyLevel.LEVEL_0_MANUAL
        else:
            level = profile.level

        # Normalise risk string
        risk = action_risk.lower().strip() if action_risk else "low"

        # Risk hierarchy: low=0, medium=1, high=2, critical=3
        risk_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        risk_rank = risk_order.get(risk, 0)

        # Determine auto-approval threshold per level
        # Level 0,1 -> threshold -1 (nothing auto)
        # Level 2   -> threshold 0 (only low)
        # Level 3   -> threshold 1 (low + medium)
        # Level 4   -> threshold 2 (low + medium + high)
        # Level 5   -> threshold 3 (all)
        approval_threshold = {
            0: -1,
            1: -1,
            2: 0,
            3: 1,
            4: 2,
            5: 3,
        }

        threshold = approval_threshold.get(int(level), -1)
        auto_approved = risk_rank <= threshold
        requires_approval = not auto_approved

        if int(level) <= 1:
            reason = f"Level {int(level)} requires human approval for all actions"
        elif auto_approved:
            reason = f"Level {int(level)} auto-approves {risk}-risk actions"
        else:
            reason = (
                f"Level {int(level)} does not auto-approve {risk}-risk actions; "
                f"human approval required"
            )

        return {
            "agent_id": agent_id,
            "level": int(level),
            "action_auto_approved": auto_approved,
            "requires_approval": requires_approval,
            "reason": reason,
        }

    def record_action(
        self,
        agent_id: str,
        success: bool,
        triggered_review: bool = False,
    ) -> None:
        """Record an action outcome in the agent's track record.

        Args:
            agent_id: The agent identifier.
            success: Whether the action succeeded.
            triggered_review: Whether this action triggered a human review.
        """
        profile = self._profiles.get(agent_id)
        if profile is None:
            return

        profile.track_record["total_actions"] += 1
        if success:
            profile.track_record["successes"] += 1
        else:
            profile.track_record["failures"] += 1
        if triggered_review:
            profile.track_record["reviews_triggered"] += 1

        self._persist_profile(profile)

        # Автоматическая корректировка уровня после записи
        self._auto_adjust_level(agent_id)

    def _auto_adjust_level(self, agent_id: str) -> None:
        """Automatically promote or demote agent based on track record."""
        profile = self._profiles.get(agent_id)
        if profile is None:
            return

        promote_result = self.should_promote(agent_id)
        demote_result = self.should_demote(agent_id)

        current_level = int(profile.level)

        if promote_result.get("should_promote") and current_level < 5:
            new_level = promote_result["suggested_level"]
            profile.level = AutonomyLevel(new_level)
            profile.metadata["auto_promoted_at"] = self.db.now_iso() if self.db else ""
            self._persist_profile(profile)

        elif demote_result.get("should_demote") and current_level > 0:
            new_level = demote_result["suggested_level"]
            profile.level = AutonomyLevel(new_level)
            profile.metadata["auto_demoted_at"] = self.db.now_iso() if self.db else ""
            self._persist_profile(profile)

    def should_promote(self, agent_id: str) -> dict:
        """Evaluate whether an agent's track record warrants promotion.

        Rule: total_actions >= 50 and success_rate > 0.95 and current level < 5.

        Args:
            agent_id: The agent identifier.

        Returns:
            Dict with promotion evaluation details.
        """
        profile = self._profiles.get(agent_id)
        if profile is None:
            return {
                "agent_id": agent_id,
                "current_level": 0,
                "should_promote": False,
                "suggested_level": 0,
                "success_rate": 0.0,
                "total_actions": 0,
                "reason": "No profile found for agent",
            }

        tr = profile.track_record
        total = tr["total_actions"]
        successes = tr["successes"]
        success_rate = successes / total if total > 0 else 0.0
        current = int(profile.level)

        if total < 50:
            promote = False
            suggested = current
            reason = f"Insufficient action history: {total}/50 required"
        elif success_rate <= 0.95:
            promote = False
            suggested = current
            reason = f"Success rate {success_rate:.2%} does not meet 95% threshold"
        elif current >= 5:
            promote = False
            suggested = 5
            reason = "Agent is already at maximum autonomy level"
        else:
            promote = True
            suggested = current + 1
            reason = (
                f"Agent meets promotion criteria: {total} actions, "
                f"{success_rate:.2%} success rate"
            )

        return {
            "agent_id": agent_id,
            "current_level": current,
            "should_promote": promote,
            "suggested_level": suggested,
            "success_rate": round(success_rate, 4),
            "total_actions": total,
            "reason": reason,
        }

    def should_demote(self, agent_id: str) -> dict:
        """Evaluate whether an agent's track record warrants demotion.

        Rule: total_actions >= 20 and success_rate < 0.7 and current level > 0.

        Args:
            agent_id: The agent identifier.

        Returns:
            Dict with demotion evaluation details.
        """
        profile = self._profiles.get(agent_id)
        if profile is None:
            return {
                "agent_id": agent_id,
                "current_level": 0,
                "should_demote": False,
                "suggested_level": 0,
                "success_rate": 0.0,
                "reason": "No profile found for agent",
            }

        tr = profile.track_record
        total = tr["total_actions"]
        successes = tr["successes"]
        success_rate = successes / total if total > 0 else 0.0
        current = int(profile.level)

        if total < 20:
            demote = False
            suggested = current
            reason = f"Insufficient action history: {total}/20 required"
        elif success_rate >= 0.7:
            demote = False
            suggested = current
            reason = f"Success rate {success_rate:.2%} is above 70% threshold"
        elif current <= 0:
            demote = False
            suggested = 0
            reason = "Agent is already at minimum autonomy level"
        else:
            demote = True
            suggested = max(0, current - 1)
            reason = (
                f"Agent meets demotion criteria: {total} actions, "
                f"{success_rate:.2%} success rate below 70%"
            )

        return {
            "agent_id": agent_id,
            "current_level": current,
            "should_demote": demote,
            "suggested_level": suggested,
            "success_rate": round(success_rate, 4),
            "reason": reason,
        }

    def get_profile(self, agent_id: str) -> dict | None:
        """Get the autonomy profile for an agent.

        Args:
            agent_id: The agent identifier.

        Returns:
            Profile dict or None if not found.
        """
        profile = self._profiles.get(agent_id)
        if profile is None:
            return None
        return self._profile_to_dict(profile)

    def list_profiles(self, level: int | None = None) -> list[dict]:
        """List all autonomy profiles, optionally filtered by level.

        Args:
            level: Filter by autonomy level.

        Returns:
            List of profile dicts.
        """
        profiles = list(self._profiles.values())
        if level is not None:
            profiles = [p for p in profiles if int(p.level) == level]
        return [self._profile_to_dict(p) for p in profiles]

    def stats(self) -> dict:
        """Return autonomy manager statistics."""
        by_level: dict[str, int] = {}
        for p in self._profiles.values():
            lvl = str(int(p.level))
            by_level[lvl] = by_level.get(lvl, 0) + 1

        auto_adjusted = sum(
            1
            for p in self._profiles.values()
            if "auto_promoted_at" in p.metadata or "auto_demoted_at" in p.metadata
        )

        return {
            "version": "3.0.0",
            "total_profiles": len(self._profiles),
            "by_level": by_level,
            "auto_adjusted_count": auto_adjusted,
            "storage": "sqlite" if self.db else "none",
        }
