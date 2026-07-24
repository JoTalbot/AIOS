"""Tests for v10.2.0 modules — Credential Manager, Price Alert System, Scraping Strategy Templates."""

from __future__ import annotations

import time

from aios_core.credential_manager import (
    CredentialEntry,
    CredentialManager,
    CredentialType,
    RotationPolicy,
    _derive_key,
    _mask_value,
    _xor_decrypt,
    _xor_encrypt,
)
from aios_core.price_alert_system import (
    AlertCondition,
    AlertPriority,
    AlertRule,
    AlertStatus,
    PriceAlert,
    PriceAlertSystem,
    PriceSnapshot,
)
from aios_core.scraping_strategy_templates import (
    BUILTIN_TEMPLATES,
    PlatformCategory,
    StrategyKind,
    StrategyTemplate,
    StrategyTemplateRegistry,
)

# ─── Credential Manager ───

class TestEncryption:
    """Tests for encryption utilities."""

    def test_xor_encrypt_decrypt_roundtrip(self) -> None:
        """Encrypt then decrypt → same value."""
        key = _derive_key("test_pass", b"salt123")
        data = b"my_secret_password"
        encrypted = _xor_encrypt(data, key)
        decrypted = _xor_decrypt(encrypted, key)
        assert decrypted == data

    def test_xor_encrypt_empty(self) -> None:
        """Empty data → empty encrypted."""
        key = _derive_key("pass", b"salt")
        assert _xor_encrypt(b"", key) == b""

    def test_xor_different_keys_different_output(self) -> None:
        """Different keys → different encrypted output."""
        key1 = _derive_key("pass1", b"salt1")
        key2 = _derive_key("pass2", b"salt2")
        data = b"hello"
        e1 = _xor_encrypt(data, key1)
        e2 = _xor_encrypt(data, key2)
        assert e1 != e2

    def test_derive_key(self) -> None:
        """Key derivation produces 32-byte key."""
        key = _derive_key("password", b"salt")
        assert len(key) == 32

    def test_derive_key_same_inputs_same_output(self) -> None:
        """Same passphrase + salt → same key."""
        key1 = _derive_key("pass", b"salt")
        key2 = _derive_key("pass", b"salt")
        assert key1 == key2

    def test_mask_value(self) -> None:
        """Mask value shows last 4 chars."""
        assert _mask_value("secret123") == "*****t123"  # 9 chars: 5 stars + last 4 "t123"
        assert _mask_value("abcd") == "****"  # 4 chars → all stars
        assert _mask_value("x") == "****"


class TestCredentialEntry:
    """Tests for CredentialEntry dataclass."""

    def test_age_days(self) -> None:
        """Age calculation."""
        entry = CredentialEntry(
            credential_id="c1", platform="olx",
            credential_type=CredentialType.PASSWORD,
            created_at=time.time() - 86400,
        )
        assert entry.age_days >= 1.0

    def test_days_until_expiry(self) -> None:
        """Expiry countdown."""
        entry = CredentialEntry(
            credential_id="c1", platform="olx",
            credential_type=CredentialType.PASSWORD,
            expires_at=time.time() + 7 * 86400,
        )
        assert entry.days_until_expiry >= 6.0

    def test_days_until_expiry_none(self) -> None:
        """No expiry → None."""
        entry = CredentialEntry(
            credential_id="c1", platform="olx",
            credential_type=CredentialType.PASSWORD,
        )
        assert entry.days_until_expiry is None

    def test_needs_rotation_monthly(self) -> None:
        """Monthly rotation after 30 days."""
        entry = CredentialEntry(
            credential_id="c1", platform="olx",
            credential_type=CredentialType.PASSWORD,
            rotation_policy=RotationPolicy.MONTHLY,
            last_rotated_at=time.time() - 35 * 86400,
        )
        assert entry.needs_rotation

    def test_needs_rotation_never(self) -> None:
        """Never rotation → False."""
        entry = CredentialEntry(
            credential_id="c1", platform="olx",
            credential_type=CredentialType.PASSWORD,
            rotation_policy=RotationPolicy.NEVER,
        )
        assert not entry.needs_rotation

    def test_needs_rotation_daily(self) -> None:
        """Daily rotation after 24 hours."""
        entry = CredentialEntry(
            credential_id="c1", platform="olx",
            credential_type=CredentialType.PASSWORD,
            rotation_policy=RotationPolicy.DAILY,
            last_rotated_at=time.time() - 86400 * 2,
        )
        assert entry.needs_rotation


class TestCredentialManager:
    """Tests for CredentialManager."""

    def test_store_and_retrieve(self) -> None:
        """Store credential then retrieve → same value."""
        mgr = CredentialManager(passphrase="test_key")
        entry = mgr.store("olx", CredentialType.PASSWORD, "my_password123")
        retrieved = mgr.retrieve(entry.credential_id)
        assert retrieved == "my_password123"

    def test_store_multiple_types(self) -> None:
        """Store different credential types."""
        mgr = CredentialManager(passphrase="test_key")
        e1 = mgr.store("olx", CredentialType.PASSWORD, "pass1")
        e2 = mgr.store("rozetka", CredentialType.API_KEY, "key123")
        e3 = mgr.store("tiktok", CredentialType.COOKIE, "session_cookie")

        assert mgr.retrieve(e1.credential_id) == "pass1"
        assert mgr.retrieve(e2.credential_id) == "key123"
        assert mgr.retrieve(e3.credential_id) == "session_cookie"

    def test_retrieve_nonexistent(self) -> None:
        """Retrieve nonexistent → None."""
        mgr = CredentialManager()
        assert mgr.retrieve("nonexistent") is None

    def test_rotate_credential(self) -> None:
        """Rotate credential with new value."""
        mgr = CredentialManager()
        entry = mgr.store("olx", CredentialType.PASSWORD, "old_pass")
        rotated = mgr.rotate(entry.credential_id, "new_pass", reason="scheduled")

        assert rotated is not None
        assert rotated.rotation_count == 1
        assert mgr.retrieve(entry.credential_id) == "new_pass"

    def test_compromise_rotation(self) -> None:
        """Compromise triggers immediate rotation."""
        mgr = CredentialManager()
        entry = mgr.store("olx", CredentialType.PASSWORD, "compromised_pass")
        rotated = mgr.compromise(entry.credential_id, "emergency_new_pass")
        assert rotated is not None
        assert mgr.retrieve(entry.credential_id) == "emergency_new_pass"

    def test_deactivate_and_activate(self) -> None:
        """Deactivate then activate credential."""
        mgr = CredentialManager()
        entry = mgr.store("olx", CredentialType.PASSWORD, "pass")
        mgr.deactivate(entry.credential_id)
        assert mgr.retrieve(entry.credential_id) is None

        mgr.activate(entry.credential_id)
        assert mgr.retrieve(entry.credential_id) == "pass"

    def test_list_credentials_masked(self) -> None:
        """List credentials shows masked values."""
        mgr = CredentialManager()
        mgr.store("olx", CredentialType.PASSWORD, "secret12345", username="user1")
        mgr.store("rozetka", CredentialType.API_KEY, "api_key_abcd")

        displays = mgr.list_credentials()
        assert len(displays) == 2
        assert displays[0].masked_value.endswith("345")  # "secret12345" → last 4 = "2345"
        assert displays[1].masked_value.endswith("abcd")

    def test_list_credentials_by_platform(self) -> None:
        """Filter credentials by platform."""
        mgr = CredentialManager()
        mgr.store("olx", CredentialType.PASSWORD, "pass1")
        mgr.store("rozetka", CredentialType.API_KEY, "key1")

        displays = mgr.list_credentials(platform="olx")
        assert len(displays) == 1

    def test_check_rotations(self) -> None:
        """Find credentials needing rotation."""
        mgr = CredentialManager()
        entry = mgr.store(
            "olx", CredentialType.PASSWORD, "pass",
            rotation_policy=RotationPolicy.MONTHLY,
        )
        # Manually set last_rotated_at to >30 days ago
        entry.last_rotated_at = time.time() - 35 * 86400

        needing = mgr.check_rotations()
        assert len(needing) >= 1

    def test_export_audit_log(self) -> None:
        """Export rotation audit log."""
        mgr = CredentialManager()
        entry = mgr.store("olx", CredentialType.PASSWORD, "pass1")
        mgr.rotate(entry.credential_id, "pass2")

        log = mgr.export_audit_log()
        assert len(log) == 1
        assert log[0]["reason"] == "scheduled"

    def test_stats(self) -> None:
        """Credential manager stats."""
        mgr = CredentialManager()
        mgr.store("olx", CredentialType.PASSWORD, "pass")
        mgr.store("rozetka", CredentialType.API_KEY, "key")

        stats = mgr.stats()
        assert stats["total_credentials"] == 2
        assert stats["active_credentials"] == 2

    def test_rekey(self) -> None:
        """Re-encrypt all credentials with new passphrase."""
        mgr = CredentialManager(passphrase="old_pass")
        entry = mgr.store("olx", CredentialType.PASSWORD, "secret_value")

        count = mgr.rekey("new_passphrase")
        assert count == 1

        # Should still retrieve correctly with new key
        retrieved = mgr.retrieve(entry.credential_id)
        assert retrieved == "secret_value"


# ─── Price Alert System ───

class TestAlertRule:
    """Tests for AlertRule dataclass."""

    def test_rule_creation(self) -> None:
        """Create alert rule."""
        rule = AlertRule(
            rule_id="r1", name="Price Drop Alert",
            condition=AlertCondition.PRICE_DROP_PCT, threshold=10.0,
        )
        assert rule.is_active
        assert rule.threshold == 10.0


class TestPriceAlert:
    """Tests for PriceAlert dataclass."""

    def test_alert_to_dict(self) -> None:
        """Serialize alert to dict."""
        alert = PriceAlert(
            alert_id="a1", rule_id="r1", platform="olx",
            fingerprint="fp1", title="iPhone",
            condition=AlertCondition.PRICE_DROP_PCT,
            old_price=100, new_price=80, change_pct=-20,
            message="Price dropped 20%",
        )
        d = alert.to_dict()
        assert d["platform"] == "olx"
        assert d["change_pct"] == -20


class TestPriceAlertSystem:
    """Tests for PriceAlertSystem."""

    def test_add_rule(self) -> None:
        """Add alert rule."""
        system = PriceAlertSystem()
        rule = system.create_rule("Price Drop 10%", AlertCondition.PRICE_DROP_PCT, threshold=10.0)
        assert rule.rule_id.startswith("rule_")

    def test_check_price_drop(self) -> None:
        """Price drop triggers alert."""
        system = PriceAlertSystem()
        system.create_rule("Drop Alert", AlertCondition.PRICE_DROP_PCT, threshold=10.0)

        snapshot = PriceSnapshot(
            fingerprint="iphone", platform="olx", title="iPhone 15",
            current_price=80, previous_price=100,
        )
        alerts = system.check_prices([snapshot])
        assert len(alerts) >= 1
        assert alerts[0].condition == AlertCondition.PRICE_DROP_PCT

    def test_check_price_increase(self) -> None:
        """Price increase triggers alert."""
        system = PriceAlertSystem()
        system.create_rule("Increase Alert", AlertCondition.PRICE_INCREASE_PCT, threshold=20.0)

        snapshot = PriceSnapshot(
            fingerprint="macbook", platform="olx", title="MacBook",
            current_price=120, previous_price=100,
        )
        alerts = system.check_prices([snapshot])
        assert len(alerts) >= 1

    def test_check_below_threshold(self) -> None:
        """Price below threshold triggers alert."""
        system = PriceAlertSystem()
        system.create_rule("Cheap Alert", AlertCondition.BELOW_THRESHOLD, threshold=500.0)

        snapshot = PriceSnapshot(
            fingerprint="phone", platform="olx", title="Phone",
            current_price=400,
        )
        alerts = system.check_prices([snapshot])
        assert len(alerts) >= 1

    def test_check_above_threshold(self) -> None:
        """Price above threshold triggers alert."""
        system = PriceAlertSystem()
        system.create_rule("Expensive Alert", AlertCondition.ABOVE_THRESHOLD, threshold=50000.0)

        snapshot = PriceSnapshot(
            fingerprint="car", platform="olx", title="BMW",
            current_price=60000,
        )
        alerts = system.check_prices([snapshot])
        assert len(alerts) >= 1

    def test_no_alert_when_no_drop(self) -> None:
        """No price drop → no alert."""
        system = PriceAlertSystem()
        system.create_rule("Drop 10%", AlertCondition.PRICE_DROP_PCT, threshold=10.0)

        snapshot = PriceSnapshot(
            fingerprint="iphone", platform="olx", title="iPhone",
            current_price=99, previous_price=100,  # 1% drop, not enough
        )
        alerts = system.check_prices([snapshot])
        assert len(alerts) == 0

    def test_fire_alert(self) -> None:
        """Fire alert stores in history."""
        system = PriceAlertSystem()
        alert = PriceAlert(
            alert_id="a1", rule_id="r1", platform="olx",
            fingerprint="fp1", title="Test",
            condition=AlertCondition.PRICE_DROP_PCT,
            message="Test alert",
        )
        fired = system.fire_alert(alert)
        assert fired.status == AlertStatus.DELIVERED

    def test_check_and_fire(self) -> None:
        """Check and fire in one step."""
        system = PriceAlertSystem()
        system.create_rule("Drop 10%", AlertCondition.PRICE_DROP_PCT, threshold=10.0)

        snapshots = [
            PriceSnapshot(
                fingerprint="iphone", platform="olx", title="iPhone",
                current_price=80, previous_price=100,
            ),
        ]
        fired = system.check_and_fire(snapshots)
        assert len(fired) >= 1

    def test_cooldown_suppression(self) -> None:
        """Cooldown suppresses duplicate alerts."""
        system = PriceAlertSystem(default_cooldown=120.0)
        system.create_rule("Drop 5%", AlertCondition.PRICE_DROP_PCT, threshold=5.0, cooldown_minutes=120)

        snapshot = PriceSnapshot(
            fingerprint="iphone", platform="olx", title="iPhone",
            current_price=90, previous_price=100,
        )
        # First check → alert
        alerts1 = system.check_and_fire([snapshot])
        assert len(alerts1) >= 1

        # Second check immediately → suppressed by cooldown
        alerts2 = system.check_prices([snapshot])
        assert len(alerts2) == 0

    def test_acknowledge_alert(self) -> None:
        """Acknowledge an alert."""
        system = PriceAlertSystem()
        alert = PriceAlert(
            alert_id="a1", rule_id="r1", platform="olx",
            fingerprint="fp1", title="Test",
            condition=AlertCondition.PRICE_DROP_PCT,
            message="Test",
        )
        system.fire_alert(alert)
        ack = system.acknowledge("a1")
        assert ack.status == AlertStatus.ACKNOWLEDGED

    def test_get_alerts(self) -> None:
        """Retrieve alert history."""
        system = PriceAlertSystem()
        system.fire_alert(PriceAlert(
            alert_id="a1", rule_id="r1", platform="olx",
            fingerprint="fp1", title="Test",
            condition=AlertCondition.PRICE_DROP_PCT,
            priority=AlertPriority.CRITICAL,
            message="Test",
        ))
        alerts = system.get_alerts(priority=AlertPriority.CRITICAL)
        assert len(alerts) == 1

    def test_digest(self) -> None:
        """Create alert digest."""
        system = PriceAlertSystem()
        system.fire_alert(PriceAlert(
            alert_id="a1", rule_id="r1", platform="olx",
            fingerprint="fp1", title="Test",
            condition=AlertCondition.PRICE_DROP_PCT,
            priority=AlertPriority.NORMAL,
            message="Test",
        ))
        digest = system.digest()
        assert digest["total_alerts"] == 1

    def test_stats(self) -> None:
        """Alert system stats."""
        system = PriceAlertSystem()
        system.create_rule("Rule1", AlertCondition.PRICE_DROP_PCT, threshold=10.0)
        stats = system.stats()
        assert stats["rules_count"] == 1

    def test_platform_filter(self) -> None:
        """Platform filter in check_prices."""
        system = PriceAlertSystem()
        system.create_rule("OLX Drop", AlertCondition.PRICE_DROP_PCT, threshold=10.0, platform="olx")

        # OLX snapshot → alert
        snap_olx = PriceSnapshot(
            fingerprint="fp1", platform="olx", title="iPhone",
            current_price=80, previous_price=100,
        )
        # Rozetka snapshot → no alert (wrong platform)
        snap_roz = PriceSnapshot(
            fingerprint="fp2", platform="rozetka", title="iPhone",
            current_price=80, previous_price=100,
        )
        alerts = system.check_prices([snap_olx, snap_roz])
        assert len(alerts) == 1  # Only OLX matches

    def test_availability_change(self) -> None:
        """Availability change alert."""
        system = PriceAlertSystem()
        rule = system.create_rule("Availability", AlertCondition.AVAILABILITY_CHANGE)
        rule.metadata["prev_available"] = True

        snap = PriceSnapshot(
            fingerprint="fp1", platform="olx", title="iPhone",
            current_price=100, is_available=False,
        )
        alerts = system.check_prices([snap])
        assert len(alerts) >= 1

    def test_remove_rule(self) -> None:
        """Remove alert rule."""
        system = PriceAlertSystem()
        rule = system.create_rule("Test Rule", AlertCondition.PRICE_DROP_PCT, threshold=10.0)
        removed = system.remove_rule(rule.rule_id)
        assert removed
        assert len(system._rules) == 0


# ─── Scraping Strategy Templates ───

class TestStrategyTemplate:
    """Tests for StrategyTemplate dataclass."""

    def test_template_to_dict(self) -> None:
        """Serialize template to dict."""
        t = StrategyTemplate(
            template_id="test", name="Test Template",
            kind=StrategyKind.COLLECTOR, platform="olx",
        )
        d = t.to_dict()
        assert d["template_id"] == "test"
        assert d["kind"] == "collector"


class TestStrategyTemplateRegistry:
    """Tests for StrategyTemplateRegistry."""

    def test_builtin_templates_loaded(self) -> None:
        """Built-in templates loaded on init."""
        registry = StrategyTemplateRegistry()
        templates = registry.list_templates()
        assert len(templates) >= len(BUILTIN_TEMPLATES)

    def test_get_template(self) -> None:
        """Get template by ID."""
        registry = StrategyTemplateRegistry()
        t = registry.get("olx_collector")
        assert t is not None
        assert t.name == "OLX Collector"

    def test_list_by_platform(self) -> None:
        """List templates for specific platform."""
        registry = StrategyTemplateRegistry()
        olx_templates = registry.list_templates(platform="olx")
        assert len(olx_templates) >= 2

    def test_list_by_kind(self) -> None:
        """List templates by kind."""
        registry = StrategyTemplateRegistry()
        collectors = registry.list_templates(kind=StrategyKind.COLLECTOR)
        assert len(collectors) >= 1

    def test_register_custom_template(self) -> None:
        """Register custom template."""
        registry = StrategyTemplateRegistry()
        custom = StrategyTemplate(
            template_id="my_template", name="My Custom Strategy",
            kind=StrategyKind.MONITOR, platform="custom",
        )
        registry.register(custom)
        assert registry.get("my_template") is not None

    def test_clone_template(self) -> None:
        """Clone template with overrides."""
        registry = StrategyTemplateRegistry()
        cloned = registry.clone(
            "olx_collector",
            name="OLX Fast Collector",
            params_override={"max_pages": 20, "page_delay_ms": 500},
        )
        assert cloned is not None
        assert cloned.name == "OLX Fast Collector"
        assert cloned.params["max_pages"] == 20

    def test_clone_nonexistent(self) -> None:
        """Clone nonexistent template → None."""
        registry = StrategyTemplateRegistry()
        result = registry.clone("nonexistent")
        assert result is None

    def test_validate_template(self) -> None:
        """Validate template configuration."""
        registry = StrategyTemplateRegistry()
        good_template = StrategyTemplate(
            template_id="t1", name="Good Template",
            params={"timeout": 30},
            sections=["cards", "detail"],
            rate_limits={"requests_per_minute": 30, "concurrent": 2},
            retry_config={"max_retries": 3},
        )
        errors = registry.validate(good_template)
        assert len(errors) == 0

    def test_validate_bad_template(self) -> None:
        """Validate template with errors."""
        registry = StrategyTemplateRegistry()
        bad_template = StrategyTemplate(
            template_id="t2", name="",  # Missing name
            params={"delay": -5},       # Negative param
            sections=[],                 # No sections
            rate_limits={"requests_per_minute": 200},  # Too aggressive
            retry_config={"max_retries": 20},          # Too many retries
        )
        errors = registry.validate(bad_template)
        assert len(errors) >= 3

    def test_compose_templates(self) -> None:
        """Compose hybrid template from multiple sources."""
        registry = StrategyTemplateRegistry()
        composed = registry.compose(
            ["olx_collector", "olx_autowatch"],
            name="OLX Full Combo",
        )
        assert composed is not None
        assert composed.kind == StrategyKind.HYBRID
        assert "cards" in composed.sections

    def test_adapt_template(self) -> None:
        """Adapt template for different platform."""
        registry = StrategyTemplateRegistry()
        adapted = registry.adapt(
            "olx_collector", "rozetka",
            PlatformCategory.ECOMMERCE,
        )
        assert adapted is not None
        assert adapted.platform == "rozetka"
        assert adapted.platform_category == PlatformCategory.ECOMMERCE
        # Rate should be lower for ecommerce
        assert adapted.rate_limits["requests_per_minute"] < 30

    def test_detect_category(self) -> None:
        """Auto-detect platform category."""
        registry = StrategyTemplateRegistry()
        assert registry._detect_category("olx") == PlatformCategory.MARKETPLACE
        assert registry._detect_category("rozetka") == PlatformCategory.ECOMMERCE
        assert registry._detect_category("whatsapp") == PlatformCategory.MESSENGER

    def test_stats(self) -> None:
        """Registry stats."""
        registry = StrategyTemplateRegistry()
        stats = registry.stats()
        assert stats["total_templates"] >= len(BUILTIN_TEMPLATES)
        assert stats["builtin_templates"] >= len(BUILTIN_TEMPLATES)

    def test_list_builtin_only(self) -> None:
        """List only built-in templates."""
        registry = StrategyTemplateRegistry()
        registry.register(StrategyTemplate(
            template_id="custom1", name="Custom",
            kind=StrategyKind.COLLECTOR,
        ))
        builtins = registry.list_templates(builtin_only=True)
        customs = registry.list_templates(builtin_only=False)
        assert len(builtins) < len(customs)

    def test_compose_nonexistent(self) -> None:
        """Compose with nonexistent template → None."""
        registry = StrategyTemplateRegistry()
        result = registry.compose(["nonexistent_id"])
        assert result is None
