"""AI Product Manager - Automated Product Development for AIOS v10.10.0.

Automated product management: ideation, roadmapping, feature
prioritization (RICE scoring), sprint planning, stakeholder
tracking, competitive analysis, and KPI metrics.

Classes:
    Product     — product lifecycle tracker
    Roadmap     — quarterly milestone plan
    Feature     — prioritized feature item
    AIProductManager — full PM engine
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

PRODUCT_STAGES = [
    "ideation",
    "validation",
    "development",
    "launch",
    "growth",
    "maturity",
]


@dataclass
class Feature:
    """Prioritized feature item with RICE scoring."""

    name: str
    description: str = ""
    reach: int = 1000  # users affected
    impact: float = 2.0  # 0.25×, 0.5×, 1×, 2×, 3×
    confidence: float = 0.8  # 0–1
    effort: float = 2.0  # person-weeks
    priority: float = 0.0  # computed RICE score
    status: str = "planned"

    def compute_rice(self) -> float:
        """Compute RICE priority score."""
        self.priority = (self.reach * self.impact * self.confidence) / max(
            self.effort, 0.5
        )
        return self.priority


@dataclass
class Product:
    """Product lifecycle tracker."""

    name: str
    vision: str
    status: str = "ideation"
    metrics: dict[str, float] = field(default_factory=dict)
    features: list[Feature] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def __getitem__(self, key):
        return getattr(self, key)

    def __contains__(self, key):
        return hasattr(self, key)

    def advance_stage(self) -> str:
        """Advance product to next lifecycle stage."""
        idx = PRODUCT_STAGES.index(self.status)
        if idx < len(PRODUCT_STAGES) - 1:
            self.status = PRODUCT_STAGES[idx + 1]
        return self.status

    def add_metric(self, key: str, value: float) -> None:
        """Track a KPI metric."""
        self.metrics[key] = value


@dataclass
class Roadmap:
    """Quarterly milestone plan."""

    product: str
    quarters: int
    milestones: list[str]
    features_per_quarter: dict[str, list[str]] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


class AIProductManager:
    """Automated product management and roadmap planning agent."""

    def __init__(self) -> None:
        self.products: list[Product] = []
        self.roadmaps: list[Roadmap] = []
        self._stakeholders: dict[str, str] = {}

    def create_product(self, name: str, vision: str) -> Product:
        """Create a product in ideation stage with *name* and *vision*."""
        product = Product(
            name=name, vision=vision, status="ideation", metrics={"awareness": 0.0}
        )
        self.products.append(product)
        logger.info("Created product %s", name)
        return product

    def create_roadmap(self, product: Product, quarters: int = 4) -> Roadmap:
        """Generate a quarterly roadmap for *product*."""
        milestones = [f"Q{i + 1}: Core feature {i + 1}" for i in range(quarters)]
        fpq: dict[str, list[str]] = {}
        for i in range(quarters):
            fpq[f"Q{i + 1}"] = [
                f.name for f in product.features[i * 2 : (i + 1) * 2]
            ] or [f"Feature {i + 1}"]
        roadmap = Roadmap(
            product=product.name,
            quarters=quarters,
            milestones=milestones,
            features_per_quarter=fpq,
        )
        self.roadmaps.append(roadmap)
        return roadmap

    def prioritize_features(self, features: list[Feature]) -> list[Feature]:
        """Prioritize features using RICE scoring."""
        for f in features:
            f.compute_rice()
        return sorted(features, key=lambda f: f.priority, reverse=True)

    def add_feature(self, product: Product, feature: Feature) -> Feature:
        """Add a feature to a product and compute its priority."""
        feature.compute_rice()
        product.features.append(feature)
        return feature

    def competitive_analysis(self, market: str) -> dict[str, Any]:
        """Generate competitive analysis for a market segment."""
        competitors = random.randint(3, 8)
        return {
            "market": market,
            "competitors": competitors,
            "market_size": competitors * 100000,
            "avg_price": round(random.uniform(10, 100), 2),
            "growth_rate": round(random.uniform(0.05, 0.3), 2),
            "opportunity_score": round(random.uniform(0.4, 0.9), 2),
        }

    def track_kpi(self, product: Product, kpi_name: str, value: float) -> None:
        """Track a KPI metric for a product."""
        product.add_metric(kpi_name, value)

    def stakeholder_register(self, name: str, role: str) -> None:
        """Register a stakeholder."""
        self._stakeholders[name] = role

    def stats(self) -> dict[str, Any]:
        """Return counts of products and roadmaps."""
        return {
            "products": len(self.products),
            "roadmaps": len(self.roadmaps),
            "stakeholders": len(self._stakeholders),
            "total_features": sum(len(p.features) for p in self.products),
        }
