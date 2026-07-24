"""AI Startup Simulator for AIOS v10.9.0.

AI startup operations simulation with team management,
funding, product launches, metrics tracking, runway
calculation, and valuation estimation.

Classes:
    StartupMetrics — startup KPI tracker
    AIStartup      — full startup simulator
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class StartupMetrics:
    """Startup KPI tracker."""
    users: int = 0
    revenue: float = 0.0
    monthly_growth: float = 0.1
    churn_rate: float = 0.05
    burn_rate: float = 0.0


class AIStartup:
    """Full AI startup simulator.

    Features:
    - Team hiring and management
    - Funding rounds
    - Product launches with user/revenue tracking
    - Runway calculation
    - Valuation estimation
    - Metrics tracking
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.team: list[dict[str, Any]] = []
        self.funding: float = 0.0
        self.products: list[dict[str, Any]] = []
        self.metrics = StartupMetrics()
        self._created_at = time.time()
        self._funding_rounds: list[dict[str, Any]] = []

    def hire(self, role: str, skill_level: float) -> None:
        """Hire a team member (backward-compatible)."""
        self.team.append({"role": role, "skill": skill_level, "hired_at": time.time()})
        self.metrics.burn_rate += skill_level * 5000  # monthly cost

    def raise_funding(self, amount: float, round_name: str = "") -> None:
        """Raise a funding round (backward-compatible)."""
        self.funding += amount
        self._funding_rounds.append({
            "amount": amount, "round": round_name or f"round_{len(self._funding_rounds) + 1}",
            "timestamp": time.time(),
        })

    def launch_product(self, product: dict[str, Any]) -> None:
        """Launch a product (backward-compatible)."""
        self.products.append(product)
        self.metrics.users += 1000
        self.metrics.revenue += product.get("revenue", 1000)

    def runway_months(self) -> float:
        """Calculate runway in months."""
        if self.metrics.burn_rate <= 0:
            return float('inf')
        return round(self.funding / self.metrics.burn_rate, 2)

    def valuation(self) -> float:
        """Estimate valuation based on metrics."""
        if self.metrics.revenue <= 0:
            return 0.0
        # Simple: revenue * multiplier + team value
        revenue_multiplier = 10 if self.metrics.revenue > 100000 else 5
        team_value = sum(m["skill"] * 100000 for m in self.team)
        return round(self.metrics.revenue * revenue_multiplier + team_value, 2)

    def growth_projection(self, months: int = 12) -> dict[str, Any]:
        """Project growth over N months."""
        users = self.metrics.users
        revenue = self.metrics.revenue
        for _ in range(months):
            users = int(users * (1 + self.metrics.monthly_growth))
            users = int(users * (1 - self.metrics.churn_rate))
            revenue *= (1 + self.metrics.monthly_growth)

        return {
            "projected_users": users,
            "projected_revenue": round(revenue, 2),
            "months": months,
        }

    def stats(self) -> dict[str, Any]:
        """Return summary statistics (backward-compatible)."""
        avg_skill = (sum(m["skill"] for m in self.team) / len(self.team)) if self.team else 0
        return {
            "name": self.name,
            "team_size": len(self.team),
            "avg_skill": round(avg_skill, 2),
            "funding": self.funding,
            "products": len(self.products),
            "users": self.metrics.users,
            "revenue": self.metrics.revenue,
            "runway_months": self.runway_months(),
        }
