"""Scraping strategy templates — pre-built configurations for common patterns.

Provides:
- StrategyTemplate: reusable configuration for scraping sessions
- Built-in templates: OLX collector, Rozetka ecommerce, TikTok Shop, etc.
- Template registry: store, retrieve, clone templates
- Template validation: check parameter ranges and compatibility
- Template composition: combine multiple templates into hybrid strategies
- Dynamic adaptation: adjust template based on platform capabilities

Templates encode best-practice configurations discovered through
A/B testing and fleet scheduling optimization.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StrategyKind(Enum):
    """Types of scraping strategies."""

    COLLECTOR = "collector"  # Gather listings/items
    MONITOR = "monitor"  # Watch for changes
    PRICE_TRACKER = "price_tracker"  # Track price changes
    MESSENGER = "messenger"  # Send/receive messages
    AUTOWATCH = "autowatch"  # Automatic watch cycle
    FULL_AGENT = "full_agent"  # Complete scraping agent
    HYBRID = "hybrid"  # Combination of multiple strategies


class PlatformCategory(Enum):
    """Platform categories for template matching."""

    MARKETPLACE = "marketplace"  # OLX, Bigl, Prom, Shafa
    ECOMMERCE = "ecommerce"  # Rozetka
    SOCIAL_SHOP = "social_shop"  # TikTok Shop, Facebook Marketplace
    MESSENGER = "messenger"  # WhatsApp, Viber, Telegram
    SOCIAL_MEDIA = "social_media"  # Instagram


@dataclass
class StrategyTemplate:
    """A reusable scraping strategy configuration."""

    template_id: str
    name: str
    kind: StrategyKind = StrategyKind.COLLECTOR
    platform: str = ""  # Target platform
    platform_category: PlatformCategory = PlatformCategory.MARKETPLACE
    description: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    sections: list[str] = field(default_factory=list)  # Enabled sections
    schedule: dict[str, Any] = field(default_factory=dict)  # Cron-like schedule
    rate_limits: dict[str, int] = field(default_factory=dict)  # Rate limit config
    retry_config: dict[str, Any] = field(default_factory=dict)  # Retry behavior
    is_builtin: bool = False
    version: str = "1.0"
    created_at: float = field(default_factory=time.time)
    updated_at: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize template to dict."""
        return {
            "template_id": self.template_id,
            "name": self.name,
            "kind": self.kind.value,
            "platform": self.platform,
            "platform_category": self.platform_category.value,
            "description": self.description,
            "params": self.params,
            "sections": self.sections,
            "schedule": self.schedule,
            "rate_limits": self.rate_limits,
            "retry_config": self.retry_config,
            "version": self.version,
        }


# ─── Built-in Templates ───

BUILTIN_TEMPLATES: list[StrategyTemplate] = [
    StrategyTemplate(
        template_id="olx_collector",
        name="OLX Collector",
        kind=StrategyKind.COLLECTOR,
        platform="olx",
        platform_category=PlatformCategory.MARKETPLACE,
        description="Standard OLX listing collector — gather cards from search results",
        params={
            "max_pages": 5,
            "page_delay_ms": 2000,
            "query": "",
            "city": "",
            "sort_by": "date",
        },
        sections=["cards", "detail", "messenger", "navigation"],
        schedule={"interval_minutes": 15, "cron": "*/15 * * * *"},
        rate_limits={"requests_per_minute": 30, "concurrent": 2},
        retry_config={"max_retries": 3, "backoff_ms": 5000, "timeout_ms": 30000},
        is_builtin=True,
    ),
    StrategyTemplate(
        template_id="olx_monitor",
        name="OLX Price Monitor",
        kind=StrategyKind.MONITOR,
        platform="olx",
        platform_category=PlatformCategory.MARKETPLACE,
        description="Monitor OLX listings for price changes and new items",
        params={
            "watch_interval_minutes": 30,
            "price_change_threshold_pct": 5.0,
            "new_item_alert": True,
        },
        sections=["cards", "detail"],
        schedule={"interval_minutes": 30, "cron": "*/30 * * * *"},
        rate_limits={"requests_per_minute": 20, "concurrent": 1},
        retry_config={"max_retries": 2, "backoff_ms": 3000},
        is_builtin=True,
    ),
    StrategyTemplate(
        template_id="rozetka_ecommerce",
        name="Rozetka Ecommerce Collector",
        kind=StrategyKind.COLLECTOR,
        platform="rozetka",
        platform_category=PlatformCategory.ECOMMERCE,
        description="Full Rozetka ecommerce scraper — cards, detail, price tracking",
        params={
            "category_url": "",
            "max_pages": 10,
            "page_delay_ms": 3000,
            "include_reviews": False,
        },
        sections=["cards", "detail", "messenger", "navigation"],
        schedule={"interval_minutes": 20, "cron": "*/20 * * * *"},
        rate_limits={"requests_per_minute": 15, "concurrent": 2},
        retry_config={"max_retries": 5, "backoff_ms": 5000},
        is_builtin=True,
    ),
    StrategyTemplate(
        template_id="tiktok_shop_collector",
        name="TikTok Shop Collector",
        kind=StrategyKind.COLLECTOR,
        platform="tiktok",
        platform_category=PlatformCategory.SOCIAL_SHOP,
        description="TikTok Shop product scraper with social metrics",
        params={
            "max_items": 100,
            "include_videos": True,
            "include_reviews": True,
        },
        sections=["cards", "detail", "messenger", "navigation"],
        schedule={"interval_minutes": 60, "cron": "0 * * * *"},
        rate_limits={"requests_per_minute": 10, "concurrent": 1},
        retry_config={"max_retries": 3, "backoff_ms": 10000},
        is_builtin=True,
    ),
    StrategyTemplate(
        template_id="fb_marketplace_collector",
        name="Facebook Marketplace Collector",
        kind=StrategyKind.COLLECTOR,
        platform="facebook",
        platform_category=PlatformCategory.SOCIAL_SHOP,
        description="Facebook Marketplace listing collector with messenger integration",
        params={
            "max_items": 50,
            "location": "",
            "category": "",
        },
        sections=["cards", "detail", "messenger", "navigation"],
        schedule={"interval_minutes": 30, "cron": "*/30 * * * *"},
        rate_limits={"requests_per_minute": 8, "concurrent": 1},
        retry_config={"max_retries": 3, "backoff_ms": 15000, "timeout_ms": 60000},
        is_builtin=True,
    ),
    StrategyTemplate(
        template_id="olx_autowatch",
        name="OLX AutoWatch Cycle",
        kind=StrategyKind.AUTOWATCH,
        platform="olx",
        platform_category=PlatformCategory.MARKETPLACE,
        description="Full OLX autowatch: collect → price alerts → stagnant → favorites",
        params={
            "stagnant_threshold_days": 7,
            "favorites_limit": 50,
            "collect_interval_minutes": 15,
        },
        sections=["cards", "detail", "messenger", "navigation"],
        schedule={"interval_minutes": 15, "cron": "*/15 * * * *"},
        rate_limits={"requests_per_minute": 25, "concurrent": 2},
        retry_config={"max_retries": 3, "backoff_ms": 5000},
        is_builtin=True,
    ),
    StrategyTemplate(
        template_id="olx_full_agent",
        name="OLX Full Agent",
        kind=StrategyKind.FULL_AGENT,
        platform="olx",
        platform_category=PlatformCategory.MARKETPLACE,
        description="Complete OLX scraping agent with all 10 modules",
        params={
            "max_pages": 10,
            "page_delay_ms": 2000,
            "dm_enabled": True,
            "autowatch_enabled": True,
            "favorites_enabled": True,
        },
        sections=["cards", "detail", "messenger", "navigation"],
        schedule={"interval_minutes": 10, "cron": "*/10 * * * *"},
        rate_limits={"requests_per_minute": 30, "concurrent": 3},
        retry_config={"max_retries": 5, "backoff_ms": 3000},
        is_builtin=True,
    ),
]


class StrategyTemplateRegistry:
    """Registry for scraping strategy templates.

    Provides:
    - register() — add template to registry
    - get() — retrieve template by ID
    - list_templates() — list templates with filters
    - clone() — clone and customize a template
    - validate() — check template parameter validity
    - compose() — combine multiple templates
    - adapt() — adjust template for specific platform
    """

    def __init__(self) -> None:
        """Initialize registry with built-in templates."""
        self._templates: dict[str, StrategyTemplate] = {}
        self._counter: int = 0

        # Load built-in templates
        for template in BUILTIN_TEMPLATES:
            self._templates[template.template_id] = template

    def _next_id(self) -> str:
        """Generate unique template ID."""
        self._counter += 1
        return f"custom_{self._counter}"

    def register(self, template: StrategyTemplate) -> StrategyTemplate:
        """Register a custom template.

        Args:
            template: StrategyTemplate to register.

        Returns:
            Registered template.
        """
        if not template.template_id:
            template.template_id = self._next_id()
        self._templates[template.template_id] = template
        return template

    def get(self, template_id: str) -> StrategyTemplate | None:
        """Get template by ID.

        Args:
            template_id: Template ID.

        Returns:
            StrategyTemplate or None.
        """
        return self._templates.get(template_id)

    def list_templates(
        self,
        platform: str | None = None,
        kind: StrategyKind | None = None,
        category: PlatformCategory | None = None,
        builtin_only: bool = False,
    ) -> list[StrategyTemplate]:
        """List templates with optional filters.

        Args:
            platform: Filter by platform.
            kind: Filter by strategy kind.
            category: Filter by platform category.
            builtin_only: Only built-in templates.

        Returns:
            List of matching StrategyTemplate instances.
        """
        results = []
        for t in self._templates.values():
            if builtin_only and not t.is_builtin:
                continue
            if platform and t.platform != platform:
                continue
            if kind and t.kind != kind:
                continue
            if category and t.platform_category != category:
                continue
            results.append(t)
        return results

    def clone(
        self,
        template_id: str,
        name: str | None = None,
        params_override: dict[str, Any] | None = None,
        schedule_override: dict[str, Any] | None = None,
    ) -> StrategyTemplate | None:
        """Clone a template with custom overrides.

        Args:
            template_id: Source template ID.
            name: New name (default: "Clone of {original}").
            params_override: Override specific params.
            schedule_override: Override schedule.

        Returns:
            Cloned StrategyTemplate, or None if source not found.
        """
        source = self._templates.get(template_id)
        if not source:
            return None

        cloned = StrategyTemplate(
            template_id=self._next_id(),
            name=name or f"Clone of {source.name}",
            kind=source.kind,
            platform=source.platform,
            platform_category=source.platform_category,
            description=source.description,
            params=dict(source.params),
            sections=list(source.sections),
            schedule=dict(source.schedule),
            rate_limits=dict(source.rate_limits),
            retry_config=dict(source.retry_config),
            is_builtin=False,
            version=source.version,
        )

        # Apply overrides
        if params_override:
            cloned.params.update(params_override)
        if schedule_override:
            cloned.schedule.update(schedule_override)

        cloned.updated_at = time.time()
        return self.register(cloned)

    def validate(self, template: StrategyTemplate) -> list[str]:
        """Validate a template configuration.

        Args:
            template: Template to validate.

        Returns:
            List of validation error messages (empty = valid).
        """
        errors = []

        # Check required fields
        if not template.name:
            errors.append("Template name is required")

        # Check params have reasonable values
        for key, value in template.params.items():
            if isinstance(value, int) and value < 0:
                errors.append(f"Parameter '{key}' must be positive")
            if isinstance(value, float) and value < 0:
                errors.append(f"Parameter '{key}' must be positive")

        # Check rate limits
        if template.rate_limits:
            rpm = template.rate_limits.get("requests_per_minute", 0)
            if rpm > 100:
                errors.append(f"Rate limit {rpm} req/min is too aggressive (max 100)")
            if rpm < 1:
                errors.append("Rate limit must be at least 1 req/min")

        # Check retry config
        if template.retry_config:
            max_retries = template.retry_config.get("max_retries", 0)
            if max_retries > 10:
                errors.append(f"Max retries {max_retries} is too high (max 10)")

        # Check sections
        if not template.sections:
            errors.append("No sections defined — template will have no functionality")

        # Check schedule
        if template.schedule:
            interval = template.schedule.get("interval_minutes", 0)
            if interval < 1:
                errors.append("Schedule interval must be at least 1 minute")

        return errors

    def compose(
        self,
        template_ids: list[str],
        name: str | None = None,
    ) -> StrategyTemplate | None:
        """Compose a hybrid template from multiple source templates.

        Args:
            template_ids: List of template IDs to combine.
            name: Name for composed template.

        Returns:
            Composed StrategyTemplate, or None.
        """
        sources = []
        for tid in template_ids:
            t = self._templates.get(tid)
            if t:
                sources.append(t)
            else:
                return None

        if not sources:
            return None

        # Merge params
        merged_params: dict[str, Any] = {}
        for s in sources:
            merged_params.update(s.params)

        # Merge sections (unique)
        merged_sections: list[str] = []
        for s in sources:
            for sec in s.sections:
                if sec not in merged_sections:
                    merged_sections.append(sec)

        # Use lowest rate limit
        merged_limits: dict[str, int] = {}
        rpm_values = [s.rate_limits.get("requests_per_minute", 30) for s in sources]
        merged_limits["requests_per_minute"] = min(rpm_values)
        concurrent_values = [s.rate_limits.get("concurrent", 1) for s in sources]
        merged_limits["concurrent"] = max(concurrent_values)

        # Use most aggressive retry
        merged_retry: dict[str, Any] = {}
        max_retry_values = [s.retry_config.get("max_retries", 3) for s in sources]
        merged_retry["max_retries"] = max(max_retry_values)
        backoff_values = [s.retry_config.get("backoff_ms", 5000) for s in sources]
        merged_retry["backoff_ms"] = min(backoff_values)

        # Use most frequent schedule
        intervals = [s.schedule.get("interval_minutes", 30) for s in sources]
        merged_schedule: dict[str, Any] = {
            "interval_minutes": min(intervals),
        }

        composed = StrategyTemplate(
            template_id=self._next_id(),
            name=name or f"Hybrid ({'+'.join(s.name for s in sources)})",
            kind=StrategyKind.HYBRID,
            platform=sources[0].platform,
            platform_category=sources[0].platform_category,
            description=f"Composed from: {', '.join(s.name for s in sources)}",
            params=merged_params,
            sections=merged_sections,
            schedule=merged_schedule,
            rate_limits=merged_limits,
            retry_config=merged_retry,
            is_builtin=False,
        )

        return self.register(composed)

    def adapt(
        self,
        template_id: str,
        target_platform: str,
        target_category: PlatformCategory | None = None,
    ) -> StrategyTemplate | None:
        """Adapt a template for a different platform.

        Adjusts rate limits, sections, and params based on platform category.

        Args:
            template_id: Source template.
            target_platform: New target platform.
            target_category: New category (auto-detected if None).

        Returns:
            Adapted StrategyTemplate, or None.
        """
        source = self._templates.get(template_id)
        if not source:
            return None

        # Auto-detect category
        category = target_category or self._detect_category(target_platform)

        # Adjust rate limits based on category
        rate_multiplier = {
            PlatformCategory.MARKETPLACE: 1.0,
            PlatformCategory.ECOMMERCE: 0.7,
            PlatformCategory.SOCIAL_SHOP: 0.5,
            PlatformCategory.MESSENGER: 0.3,
            PlatformCategory.SOCIAL_MEDIA: 0.3,
        }.get(category, 1.0)

        adapted_limits = dict(source.rate_limits)
        rpm = adapted_limits.get("requests_per_minute", 30)
        adapted_limits["requests_per_minute"] = int(rpm * rate_multiplier)

        adapted = StrategyTemplate(
            template_id=self._next_id(),
            name=f"{source.name} → {target_platform}",
            kind=source.kind,
            platform=target_platform,
            platform_category=category,
            description=f"Adapted from {source.name} for {target_platform}",
            params=dict(source.params),
            sections=list(source.sections),
            schedule=dict(source.schedule),
            rate_limits=adapted_limits,
            retry_config=dict(source.retry_config),
            is_builtin=False,
        )

        return self.register(adapted)

    def _detect_category(self, platform: str) -> PlatformCategory:
        """Detect platform category from platform name.

        Args:
            platform: Platform name.

        Returns:
            PlatformCategory.
        """
        category_map = {
            "olx": PlatformCategory.MARKETPLACE,
            "bigl": PlatformCategory.MARKETPLACE,
            "prom": PlatformCategory.MARKETPLACE,
            "shafa": PlatformCategory.MARKETPLACE,
            "rozetka": PlatformCategory.ECOMMERCE,
            "tiktok": PlatformCategory.SOCIAL_SHOP,
            "facebook": PlatformCategory.SOCIAL_SHOP,
            "whatsapp": PlatformCategory.MESSENGER,
            "viber": PlatformCategory.MESSENGER,
            "telegram": PlatformCategory.MESSENGER,
            "instagram": PlatformCategory.SOCIAL_MEDIA,
        }
        return category_map.get(platform, PlatformCategory.MARKETPLACE)

    def stats(self) -> dict[str, Any]:
        """Registry statistics.

        Returns:
            Dict with template counts and distribution.
        """
        total = len(self._templates)
        builtin = sum(1 for t in self._templates.values() if t.is_builtin)
        custom = total - builtin

        kind_dist: dict[str, int] = {}
        for t in self._templates.values():
            kind_dist[t.kind.value] = kind_dist.get(t.kind.value, 0) + 1

        platform_dist: dict[str, int] = {}
        for t in self._templates.values():
            platform_dist[t.platform] = platform_dist.get(t.platform, 0) + 1

        return {
            "total_templates": total,
            "builtin_templates": builtin,
            "custom_templates": custom,
            "kind_distribution": kind_dist,
            "platform_distribution": platform_dist,
        }
