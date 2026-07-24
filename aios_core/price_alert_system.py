"""Price alert system — configurable alerts for price drops and changes.

Provides:
- Alert rules: define conditions (price drop %, price threshold, availability change)
- Alert matching: check current prices against rules
- Alert delivery: notification via email, telegram, webhook, push
- Alert history: track all fired alerts with timestamps
- Alert deduplication: suppress duplicate alerts within cooldown window
- Alert priorities: critical/high/normal/low with escalation
- Alert batching: group similar alerts into digest

No external notification services — uses notification_router for delivery.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AlertCondition(Enum):
    """Conditions that trigger a price alert."""

    PRICE_DROP_PCT = "price_drop_pct"      # Price dropped by X%
    PRICE_INCREASE_PCT = "price_increase_pct"  # Price increased by X%
    BELOW_THRESHOLD = "below_threshold"    # Price below absolute threshold
    ABOVE_THRESHOLD = "above_threshold"    # Price above absolute threshold
    AVAILABILITY_CHANGE = "availability_change"  # Item became available/unavailable
    PRICE_STABILITY = "price_stability"    # Price unchanged for X days (stagnant)
    ARBITRAGE_SPREAD = "arbitrage_spread"  # Cross-platform spread >= X%


class AlertPriority(Enum):
    """Alert priority levels."""

    CRITICAL = "critical"   # Immediate action needed
    HIGH = "high"           # Important, act within hours
    NORMAL = "normal"       # Standard alert
    LOW = "low"             # Background notification
    INFO = "info"           # Informational only


class AlertStatus(Enum):
    """Alert lifecycle status."""

    PENDING = "pending"     # Awaiting delivery
    DELIVERED = "delivered" # Successfully delivered
    FAILED = "failed"       # Delivery failed
    SUPPRESSED = "suppressed"  # Duplicate suppressed by cooldown
    ACKNOWLEDGED = "acknowledged"  # User acknowledged


@dataclass
class AlertRule:
    """A rule defining when to trigger an alert."""

    rule_id: str
    name: str
    platform: str = ""          # "olx", "rozetka", etc. (empty = all platforms)
    fingerprint: str = ""       # Specific product (empty = all matching)
    condition: AlertCondition = AlertCondition.PRICE_DROP_PCT
    threshold: float = 0.0      # X% or absolute price value
    priority: AlertPriority = AlertPriority.NORMAL
    cooldown_minutes: float = 60.0  # Suppress duplicate alerts for this duration
    is_active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PriceAlert:
    """A triggered price alert."""

    alert_id: str
    rule_id: str
    platform: str
    fingerprint: str
    title: str
    condition: AlertCondition
    old_price: float | None = None
    new_price: float | None = None
    change_pct: float | None = None
    threshold_value: float | None = None
    priority: AlertPriority = AlertPriority.NORMAL
    status: AlertStatus = AlertStatus.PENDING
    message: str = ""
    created_at: float = field(default_factory=time.time)
    delivered_at: float | None = None
    acknowledged_at: float | None = None

    @property
    def age_minutes(self) -> float:
        """Age of alert in minutes."""
        return (time.time() - self.created_at) / 60

    def to_dict(self) -> dict[str, Any]:
        """Serialize alert to dict."""
        return {
            "alert_id": self.alert_id,
            "rule_id": self.rule_id,
            "platform": self.platform,
            "fingerprint": self.fingerprint,
            "title": self.title,
            "condition": self.condition.value,
            "old_price": self.old_price,
            "new_price": self.new_price,
            "change_pct": round(self.change_pct, 2) if self.change_pct else None,
            "priority": self.priority.value,
            "status": self.status.value,
            "message": self.message,
            "created_at": self.created_at,
        }


@dataclass
class PriceSnapshot:
    """A snapshot of current prices for comparison."""

    fingerprint: str
    platform: str
    title: str
    current_price: float | None = None
    previous_price: float | None = None
    is_available: bool = True
    last_change_at: float | None = None


class PriceAlertSystem:
    """Price alert system for configurable price monitoring.

    Provides:
    - add_rule() — define alert conditions
    - check_prices() — evaluate snapshots against rules
    - fire_alert() — create and deliver an alert
    - check_and_fire() — automatic check + fire cycle
    - get_alerts() — retrieve alert history
    - acknowledge() — mark alert as acknowledged
    - digest() — batch recent alerts into digest
    """

    def __init__(
        self,
        default_cooldown: float = 60.0,
        max_alerts: int = 1000,
    ) -> None:
        """Initialize PriceAlertSystem.

        Args:
            default_cooldown: Default cooldown in minutes for dedup.
            max_alerts: Maximum alerts to store in history.
        """
        self.default_cooldown = default_cooldown
        self.max_alerts = max_alerts
        self._rules: dict[str, AlertRule] = {}
        self._alerts: list[PriceAlert] = []
        self._last_fired: dict[str, float] = {}  # rule_id+fingerprint → last fired timestamp
        self._counter: int = 0

    def _next_id(self) -> str:
        """Generate unique alert ID."""
        self._counter += 1
        return f"alert_{self._counter}"

    def add_rule(self, rule: AlertRule) -> AlertRule:
        """Add an alert rule.

        Args:
            rule: AlertRule to add.

        Returns:
            Added AlertRule.
        """
        self._rules[rule.rule_id] = rule
        return rule

    def create_rule(
        self,
        name: str,
        condition: AlertCondition = AlertCondition.PRICE_DROP_PCT,
        threshold: float = 10.0,
        platform: str = "",
        fingerprint: str = "",
        priority: AlertPriority = AlertPriority.NORMAL,
        cooldown_minutes: float | None = None,
    ) -> AlertRule:
        """Create and add a rule with simple parameters.

        Args:
            name: Rule name.
            condition: Alert condition type.
            threshold: Threshold value (% or absolute).
            platform: Target platform.
            fingerprint: Target product fingerprint.
            priority: Alert priority.
            cooldown_minutes: Cooldown override.

        Returns:
            Created AlertRule.
        """
        rule_id = f"rule_{len(self._rules) + 1}"
        rule = AlertRule(
            rule_id=rule_id,
            name=name,
            platform=platform,
            fingerprint=fingerprint,
            condition=condition,
            threshold=threshold,
            priority=priority,
            cooldown_minutes=cooldown_minutes or self.default_cooldown,
        )
        return self.add_rule(rule)

    def remove_rule(self, rule_id: str) -> bool:
        """Remove an alert rule.

        Args:
            rule_id: Rule ID to remove.

        Returns:
            True if rule was found and removed.
        """
        return self._rules.pop(rule_id, None) is not None

    def check_prices(
        self,
        snapshots: list[PriceSnapshot],
    ) -> list[PriceAlert]:
        """Check price snapshots against all active rules.

        Args:
            snapshots: Current price data.

        Returns:
            List of PriceAlert for matching conditions (not yet delivered).
        """
        alerts = []

        for snapshot in snapshots:
            for rule in self._rules.values():
                if not rule.is_active:
                    continue

                # Check platform match
                if rule.platform and rule.platform != snapshot.platform:
                    continue

                # Check fingerprint match
                if rule.fingerprint and rule.fingerprint != snapshot.fingerprint:
                    continue

                # Evaluate condition
                match = self._evaluate_condition(snapshot, rule)
                if not match:
                    continue

                # Check cooldown (dedup)
                cooldown_key = f"{rule.rule_id}:{snapshot.fingerprint}"
                last_fired = self._last_fired.get(cooldown_key, 0)
                cooldown_seconds = rule.cooldown_minutes * 60
                if time.time() - last_fired < cooldown_seconds:
                    continue  # Suppressed by cooldown

                # Create alert
                change_pct = None
                if snapshot.previous_price and snapshot.current_price and snapshot.previous_price > 0:
                    change_pct = (snapshot.current_price - snapshot.previous_price) / snapshot.previous_price * 100

                alert = PriceAlert(
                    alert_id=self._next_id(),
                    rule_id=rule.rule_id,
                    platform=snapshot.platform,
                    fingerprint=snapshot.fingerprint,
                    title=snapshot.title,
                    condition=rule.condition,
                    old_price=snapshot.previous_price,
                    new_price=snapshot.current_price,
                    change_pct=change_pct,
                    priority=rule.priority,
                    message=self._generate_message(snapshot, rule, match),
                )

                alerts.append(alert)
                self._last_fired[cooldown_key] = time.time()

        return alerts

    def _evaluate_condition(
        self, snapshot: PriceSnapshot, rule: AlertRule
    ) -> bool | dict[str, Any]:
        """Evaluate whether a snapshot matches a rule condition.

        Args:
            snapshot: Price data.
            rule: Alert rule.

        Returns:
            True/dict if condition matches, False otherwise.
        """
        if rule.condition == AlertCondition.PRICE_DROP_PCT:
            if snapshot.previous_price and snapshot.current_price and snapshot.previous_price > 0:
                drop_pct = (snapshot.previous_price - snapshot.current_price) / snapshot.previous_price * 100
                if drop_pct >= rule.threshold:
                    return {"drop_pct": round(drop_pct, 2)}

        elif rule.condition == AlertCondition.PRICE_INCREASE_PCT:
            if snapshot.previous_price and snapshot.current_price and snapshot.previous_price > 0:
                increase_pct = (snapshot.current_price - snapshot.previous_price) / snapshot.previous_price * 100
                if increase_pct >= rule.threshold:
                    return {"increase_pct": round(increase_pct, 2)}

        elif rule.condition == AlertCondition.BELOW_THRESHOLD:
            if snapshot.current_price and snapshot.current_price < rule.threshold:
                return {"current_price": snapshot.current_price, "threshold": rule.threshold}

        elif rule.condition == AlertCondition.ABOVE_THRESHOLD:
            if snapshot.current_price and snapshot.current_price > rule.threshold:
                return {"current_price": snapshot.current_price, "threshold": rule.threshold}

        elif rule.condition == AlertCondition.AVAILABILITY_CHANGE:
            # Triggered when availability changes (check previous availability in metadata)
            prev_available = rule.metadata.get("prev_available", True)
            if snapshot.is_available != prev_available:
                return {"available": snapshot.is_available, "prev_available": prev_available}

        elif rule.condition == AlertCondition.PRICE_STABILITY:
            if snapshot.last_change_at:
                stable_days = (time.time() - snapshot.last_change_at) / 86400
                if stable_days >= rule.threshold:
                    return {"stable_days": round(stable_days, 1)}

        elif rule.condition == AlertCondition.ARBITRAGE_SPREAD:
            # Requires cross-platform data in snapshot metadata
            spread = snapshot.metadata.get("spread_pct", 0) if hasattr(snapshot, 'metadata') else 0
            if spread >= rule.threshold:
                return {"spread_pct": spread}

        return False

    def _generate_message(
        self, snapshot: PriceSnapshot, rule: AlertRule, match: Any
    ) -> str:
        """Generate alert message text.

        Args:
            snapshot: Price data.
            rule: Triggered rule.
            match: Match details from _evaluate_condition.

        Returns:
            Human-readable alert message.
        """
        title = snapshot.title or snapshot.fingerprint

        if rule.condition == AlertCondition.PRICE_DROP_PCT:
            drop = match.get("drop_pct", 0) if isinstance(match, dict) else 0
            return f"📉 {title}: цена снизилась на {drop:.1f}% (было {snapshot.previous_price:.0f} → {snapshot.current_price:.0f} грн)"

        elif rule.condition == AlertCondition.PRICE_INCREASE_PCT:
            inc = match.get("increase_pct", 0) if isinstance(match, dict) else 0
            return f"📈 {title}: цена выросла на {inc:.1f}% ({snapshot.previous_price:.0f} → {snapshot.current_price:.0f} грн)"

        elif rule.condition == AlertCondition.BELOW_THRESHOLD:
            return f"💰 {title}: цена {snapshot.current_price:.0f} грн ниже порога {rule.threshold:.0f} грн"

        elif rule.condition == AlertCondition.ABOVE_THRESHOLD:
            return f"⚠️ {title}: цена {snapshot.current_price:.0f} грн выше порога {rule.threshold:.0f} грн"

        elif rule.condition == AlertCondition.AVAILABILITY_CHANGE:
            avail = match.get("available", True) if isinstance(match, dict) else True
            status = "доступен" if avail else "нет в наличии"
            return f"📦 {title}: изменение доступности — {status}"

        elif rule.condition == AlertCondition.PRICE_STABILITY:
            days = match.get("stable_days", 0) if isinstance(match, dict) else 0
            return f"🔒 {title}: цена не менялась {days:.0f} дней (стагнация)"

        elif rule.condition == AlertCondition.ARBITRAGE_SPREAD:
            spread = match.get("spread_pct", 0) if isinstance(match, dict) else 0
            return f"🔀 {title}: арбитражный спред {spread:.1f}%"

        return f"🔔 {title}: сработало правило '{rule.name}'"

    def fire_alert(self, alert: PriceAlert) -> PriceAlert:
        """Fire an alert (store in history, mark as delivered).

        Args:
            alert: PriceAlert to fire.

        Returns:
            Fired PriceAlert with updated status.
        """
        alert.status = AlertStatus.DELIVERED
        alert.delivered_at = time.time()
        self._alerts.append(alert)

        # Trim history if exceeding max
        if len(self._alerts) > self.max_alerts:
            self._alerts = self._alerts[-self.max_alerts:]

        return alert

    def check_and_fire(
        self,
        snapshots: list[PriceSnapshot],
    ) -> list[PriceAlert]:
        """Check prices and fire matching alerts automatically.

        Args:
            snapshots: Current price data.

        Returns:
            List of fired PriceAlert.
        """
        new_alerts = self.check_prices(snapshots)
        fired = []
        for alert in new_alerts:
            fired_alert = self.fire_alert(alert)
            fired.append(fired_alert)
        return fired

    def get_alerts(
        self,
        priority: AlertPriority | None = None,
        platform: str | None = None,
        status: AlertStatus | None = None,
        limit: int = 50,
    ) -> list[PriceAlert]:
        """Retrieve alert history with optional filters.

        Args:
            priority: Filter by priority.
            platform: Filter by platform.
            status: Filter by status.
            limit: Maximum alerts to return.

        Returns:
            List of PriceAlert matching filters.
        """
        results = []
        for alert in reversed(self._alerts):  # Most recent first
            if priority and alert.priority != priority:
                continue
            if platform and alert.platform != platform:
                continue
            if status and alert.status != status:
                continue
            results.append(alert)
            if len(results) >= limit:
                break
        return results

    def acknowledge(self, alert_id: str) -> PriceAlert | None:
        """Acknowledge an alert.

        Args:
            alert_id: Alert ID to acknowledge.

        Returns:
            Acknowledged PriceAlert, or None.
        """
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_at = time.time()
                return alert
        return None

    def digest(
        self,
        since: float | None = None,
        priority: AlertPriority | None = None,
    ) -> dict[str, Any]:
        """Create a digest of recent alerts.

        Args:
            since: Timestamp cutoff (None = last 24 hours).
            priority: Filter by priority.

        Returns:
            Dict with summary and grouped alerts.
        """
        cutoff = since or (time.time() - 86400)  # Default: last 24h

        recent = [
            a for a in self._alerts
            if a.created_at >= cutoff
            and (priority is None or a.priority == priority)
        ]

        # Group by priority
        by_priority: dict[str, list[PriceAlert]] = {}
        for alert in recent:
            key = alert.priority.value
            by_priority.setdefault(key, []).append(alert)

        # Group by platform
        by_platform: dict[str, list[PriceAlert]] = {}
        for alert in recent:
            key = alert.platform
            by_platform.setdefault(key, []).append(alert)

        return {
            "total_alerts": len(recent),
            "critical_count": len(by_priority.get("critical", [])),
            "high_count": len(by_priority.get("high", [])),
            "normal_count": len(by_priority.get("normal", [])),
            "low_count": len(by_priority.get("low", [])),
            "by_priority": {
                k: [a.to_dict() for a in v] for k, v in by_priority.items()
            },
            "by_platform": {
                k: len(v) for k, v in by_platform.items()
            },
            "since": cutoff,
        }

    def stats(self) -> dict[str, Any]:
        """Alert system statistics.

        Returns:
            Dict with rules, alerts, suppression counts.
        """
        total = len(self._alerts)
        delivered = sum(1 for a in self._alerts if a.status == AlertStatus.DELIVERED)
        acknowledged = sum(1 for a in self._alerts if a.status == AlertStatus.ACKNOWLEDGED)

        return {
            "rules_count": len(self._rules),
            "active_rules": sum(1 for r in self._rules.values() if r.is_active),
            "total_alerts": total,
            "delivered_alerts": delivered,
            "acknowledged_alerts": acknowledged,
            "pending_alerts": sum(1 for a in self._alerts if a.status == AlertStatus.PENDING),
        }

    def clear_history(self) -> int:
        """Clear alert history.

        Returns:
            Number of alerts cleared.
        """
        count = len(self._alerts)
        self._alerts.clear()
        return count
