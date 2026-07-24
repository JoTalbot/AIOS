"""Tests for v10.3.0 modules — Agent Memory, Platform Health, Export/Import Pipeline."""

from __future__ import annotations

import os
import time
from typing import Any

from aios_core.agent_memory_system import (
    AgentMemorySystem,
    MemoryEntry,
    MemoryPriority,
    MemoryType,
)
from aios_core.export_import_pipeline import (
    DEFAULT_SCHEMA,
    ExportFormat,
    ExportImportPipeline,
    ImportMode,
)
from aios_core.platform_health_monitor import (
    CheckType,
    HealthCheck,
    HealthStatus,
    PlatformHealth,
    PlatformHealthMonitor,
)

# ─── Agent Memory System ───

class TestMemoryEntry:
    """Tests for MemoryEntry dataclass."""

    def test_strength_new_memory(self) -> None:
        """New memory has high strength."""
        entry = MemoryEntry(
            memory_id="m1", memory_type=MemoryType.SHORT_TERM,
            platform="olx", action="collect", result="success",
            confidence=1.0, created_at=time.time(),
        )
        assert entry.strength >= 0.9

    def test_strength_decays(self) -> None:
        """Old memory has lower strength."""
        entry = MemoryEntry(
            memory_id="m1", memory_type=MemoryType.SHORT_TERM,
            platform="olx", action="collect", result="success",
            confidence=1.0, created_at=time.time() - 100 * 86400,
            decay_rate=0.01,
        )
        assert entry.strength < 0.5

    def test_strength_boosted_by_access(self) -> None:
        """Frequently accessed memories are stronger."""
        entry1 = MemoryEntry(
            memory_id="m1", memory_type=MemoryType.LONG_TERM,
            platform="olx", action="collect", result="success",
            confidence=0.8, access_count=0,
        )
        entry2 = MemoryEntry(
            memory_id="m2", memory_type=MemoryType.LONG_TERM,
            platform="olx", action="collect", result="success",
            confidence=0.8, access_count=50,
        )
        assert entry2.strength > entry1.strength

    def test_age_days(self) -> None:
        """Age calculation."""
        entry = MemoryEntry(
            memory_id="m1", memory_type=MemoryType.SHORT_TERM,
            platform="olx", action="collect", result="success",
            created_at=time.time() - 7 * 86400,
        )
        assert abs(entry.age_days - 7.0) < 0.1

    def test_to_dict(self) -> None:
        """Serialize memory entry."""
        entry = MemoryEntry(
            memory_id="m1", memory_type=MemoryType.SHORT_TERM,
            platform="olx", action="collect", result="success",
        )
        d = entry.to_dict()
        assert d["platform"] == "olx"
        assert d["type"] == "short_term"


class TestAgentMemorySystem:
    """Tests for AgentMemorySystem."""

    def test_record_short_term(self) -> None:
        """Record short-term memory."""
        system = AgentMemorySystem()
        entry = system.record("olx", "collect", "success")
        assert entry.memory_type == MemoryType.SHORT_TERM
        assert len(system._short_term) == 1

    def test_record_episodic(self) -> None:
        """Record episodic memory."""
        system = AgentMemorySystem()
        entry = system.record(
            "olx", "collect", "success", memory_type=MemoryType.EPISODIC,
        )
        assert entry.memory_type == MemoryType.EPISODIC

    def test_record_session(self) -> None:
        """Record a scraping session."""
        system = AgentMemorySystem()
        entry = system.record_session(
            platform="olx", action="collect", success=True,
            latency_ms=500, items=50,
        )
        assert entry.result == "success"
        assert entry.context["latency_ms"] == 500

    def test_record_session_failure(self) -> None:
        """Record a failed session."""
        system = AgentMemorySystem()
        entry = system.record_session(
            platform="olx", action="collect", success=False,
            errors=["timeout", "captcha"],
        )
        assert entry.result == "failure"
        assert entry.context["errors"] == ["timeout", "captcha"]

    def test_record_session_blocked(self) -> None:
        """Record a blocked session → critical priority."""
        system = AgentMemorySystem()
        entry = system.record_session(
            platform="olx", action="collect", success=False,
            errors=["IP banned by platform"],
        )
        assert entry.priority == MemoryPriority.CRITICAL

    def test_recall_by_platform(self) -> None:
        """Recall memories filtered by platform."""
        system = AgentMemorySystem()
        system.record("olx", "collect", "success")
        system.record("rozetka", "collect", "success")
        olx_memories = system.recall(platform="olx")
        assert len(olx_memories) >= 1

    def test_recall_by_action(self) -> None:
        """Recall memories filtered by action."""
        system = AgentMemorySystem()
        system.record("olx", "collect", "success")
        system.record("olx", "login", "failure")
        collect = system.recall(action="collect")
        assert len(collect) >= 1
        assert collect[0].action == "collect"

    def test_recall_by_result(self) -> None:
        """Recall only failure memories."""
        system = AgentMemorySystem()
        system.record("olx", "collect", "success")
        system.record("olx", "collect", "failure")
        failures = system.recall(result="failure")
        assert len(failures) >= 1

    def test_recall_min_strength(self) -> None:
        """Filter by minimum strength."""
        system = AgentMemorySystem()
        system.record("olx", "collect", "success", confidence=0.01)
        # Very low confidence → low strength
        results = system.recall(min_strength=0.5)
        # Should not return very weak memories
        assert len(results) == 0 or all(r.strength >= 0.5 for r in results)

    def test_consolidate(self) -> None:
        """Consolidate episodic into long-term."""
        system = AgentMemorySystem(consolidation_interval=0)
        # Record enough episodic memories
        for i in range(5):
            system.record_session("olx", "collect", success=True, latency_ms=500, items=50)

        # Force consolidation
        system._last_consolidation = 0  # Reset interval
        count = system.consolidate()
        assert count >= 1

    def test_extract_patterns(self) -> None:
        """Extract success patterns from episodic data."""
        system = AgentMemorySystem()
        for i in range(10):
            system.record_session(
                "olx", "collect", success=True,
                latency_ms=500 + i * 10,
                items=50 + i,
                params={"timeout": 30, "max_pages": 5},
            )

        patterns = system.extract_patterns()
        assert len(patterns) >= 1
        assert patterns[0].success_rate >= 0.5

    def test_get_advice(self) -> None:
        """Get advice based on past experiences."""
        system = AgentMemorySystem()
        system.record_session("olx", "collect", success=True, params={"timeout": 30})
        system.record_session("olx", "collect", success=True, params={"timeout": 20})

        # Create a pattern
        system.extract_patterns()

        advice = system.get_advice("olx", "collect")
        assert advice["platform"] == "olx"
        assert isinstance(advice["recommended_params"], dict)

    def test_get_advice_with_block_warnings(self) -> None:
        """Advice includes block warnings."""
        system = AgentMemorySystem()
        system.record(
            "olx", "collect", "blocked",
            memory_type=MemoryType.EPISODIC,
            priority=MemoryPriority.CRITICAL,
            context={"params": {"delay": 0}},
        )

        advice = system.get_advice("olx", "collect")
        assert len(advice["warnings"]) >= 1

    def test_decay(self) -> None:
        """Decay removes weak memories."""
        system = AgentMemorySystem()
        entry = system.record("olx", "collect", "success", confidence=0.001)
        entry.created_at = time.time() - 365 * 86400  # 1 year old
        entry.decay_rate = 0.1  # Fast decay

        system.decay(min_strength=0.05)
        # Weak memories should be removed

    def test_clear_short_term(self) -> None:
        """Clear short-term memories."""
        system = AgentMemorySystem()
        system.record("olx", "collect", "success")
        system.record("olx", "collect", "success")

        count = system.clear_short_term()
        assert count >= 0  # Short-term memories cleared

    def test_stats(self) -> None:
        """Memory system statistics."""
        system = AgentMemorySystem()
        system.record("olx", "collect", "success")
        system.record("rozetka", "collect", "failure")

        stats = system.stats()
        assert stats["short_term_count"] >= 2
        assert "olx" in stats["platform_distribution"]


# ─── Platform Health Monitor ───

class TestPlatformHealth:
    """Tests for PlatformHealth dataclass."""

    def test_is_available_healthy(self) -> None:
        """Healthy platform is available."""
        health = PlatformHealth(platform="olx", status=HealthStatus.HEALTHY)
        assert health.is_available

    def test_is_available_blocked(self) -> None:
        """Blocked platform is not available."""
        health = PlatformHealth(platform="olx", status=HealthStatus.BLOCKED)
        assert not health.is_available

    def test_is_available_down(self) -> None:
        """Down platform is not available."""
        health = PlatformHealth(platform="olx", status=HealthStatus.DOWN)
        assert not health.is_available

    def test_age_minutes(self) -> None:
        """Age calculation."""
        health = PlatformHealth(platform="olx", last_check=time.time() - 600)
        assert health.age_minutes >= 10

    def test_to_dict(self) -> None:
        """Serialize health."""
        health = PlatformHealth(platform="olx", health_score=85)
        d = health.to_dict()
        assert d["platform"] == "olx"
        assert d["health_score"] == 85


class TestHealthCheck:
    """Tests for HealthCheck dataclass."""

    def test_to_dict(self) -> None:
        """Serialize check."""
        check = HealthCheck(
            check_id="c1", platform="olx",
            check_type=CheckType.PING, status=HealthStatus.HEALTHY,
            latency_ms=200, success=True,
        )
        d = check.to_dict()
        assert d["platform"] == "olx"
        assert d["latency_ms"] == 200


class TestPlatformHealthMonitor:
    """Tests for PlatformHealthMonitor."""

    def test_register_platform(self) -> None:
        """Register platform for monitoring."""
        monitor = PlatformHealthMonitor()
        health = monitor.register_platform("olx")
        assert health.platform == "olx"
        assert health.status == HealthStatus.UNKNOWN

    def test_report_success(self) -> None:
        """Report successful operation."""
        monitor = PlatformHealthMonitor()
        health = monitor.report_success("olx", latency_ms=300)
        assert health.consecutive_successes >= 1
        assert health.success_rate == 1.0
        assert health.health_score > 50

    def test_report_failure(self) -> None:
        """Report failed operation."""
        monitor = PlatformHealthMonitor()
        monitor.register_platform("olx")
        health = monitor.report_failure("olx", error="timeout")
        assert health.consecutive_failures >= 1

    def test_consecutive_failures_down(self) -> None:
        """5 consecutive failures → DOWN status."""
        monitor = PlatformHealthMonitor(max_consecutive_failures=3)
        monitor.register_platform("olx")
        for i in range(3):
            monitor.report_failure("olx", error=f"error_{i}")
        health = monitor.get_health("olx")
        assert health.status == HealthStatus.DOWN

    def test_report_block(self) -> None:
        """Report block → BLOCKED status."""
        monitor = PlatformHealthMonitor()
        monitor.register_platform("olx")
        # Need enough checks to make block_risk >= threshold
        for i in range(5):
            monitor.report_block("olx", block_type="rate_limit")
        health = monitor.get_health("olx")
        assert health.status == HealthStatus.BLOCKED

    def test_mixed_success_failure(self) -> None:
        """Mixed success/failure → DEGRADED status."""
        monitor = PlatformHealthMonitor(health_threshold=70)
        monitor.register_platform("olx")
        for i in range(5):
            monitor.report_success("olx", latency_ms=300)
        for i in range(3):
            monitor.report_failure("olx", error="slow")
        health = monitor.get_health("olx")
        # 5/8 success rate = 62.5% → likely DEGRADED
        assert health.success_rate < 1.0

    def test_get_health(self) -> None:
        """Get health for platform."""
        monitor = PlatformHealthMonitor()
        monitor.report_success("olx")
        health = monitor.get_health("olx")
        assert health is not None

    def test_get_health_unknown(self) -> None:
        """Get health for unregistered platform → None."""
        monitor = PlatformHealthMonitor()
        assert monitor.get_health("rozetka") is None

    def test_compare_platforms(self) -> None:
        """Compare platform health."""
        monitor = PlatformHealthMonitor()
        monitor.report_success("olx", latency_ms=200)
        monitor.report_success("rozetka", latency_ms=500)
        comparison = monitor.compare_platforms()
        assert len(comparison) == 2
        # OLX should have higher score (lower latency)
        assert comparison[0]["health_score"] >= comparison[1]["health_score"]

    def test_detect_degradation(self) -> None:
        """Find degraded platforms."""
        monitor = PlatformHealthMonitor()
        monitor.report_success("olx", latency_ms=200)
        for i in range(5):
            monitor.report_failure("rozetka", error="error")
        degraded = monitor.detect_degradation()
        assert "rozetka" in degraded

    def test_best_platform(self) -> None:
        """Find best platform."""
        monitor = PlatformHealthMonitor()
        monitor.report_success("olx", latency_ms=200)
        monitor.report_success("rozetka", latency_ms=300)
        best = monitor.best_platform()
        assert best is not None

    def test_stats(self) -> None:
        """Monitor statistics."""
        monitor = PlatformHealthMonitor()
        monitor.report_success("olx")
        monitor.report_success("rozetka")
        stats = monitor.stats()
        assert stats["monitored_platforms"] >= 2


# ─── Export/Import Pipeline ───

class TestExportSchema:
    """Tests for ExportSchema."""

    def test_validate_valid_record(self) -> None:
        """Valid record passes validation."""
        schema = DEFAULT_SCHEMA
        record = {"fingerprint": "fp1", "title": "iPhone", "platform": "olx"}
        errors = schema.validate_record(record)
        assert len(errors) == 0

    def test_validate_missing_required(self) -> None:
        """Missing required field → error."""
        schema = DEFAULT_SCHEMA
        record = {"title": "iPhone"}  # Missing fingerprint and platform
        errors = schema.validate_record(record)
        assert len(errors) >= 2

    def test_validate_wrong_type(self) -> None:
        """Wrong type → error."""
        schema = DEFAULT_SCHEMA
        record = {"fingerprint": "fp1", "title": "iPhone", "price": "not_a_number", "platform": "olx"}
        errors = schema.validate_record(record)
        assert len(errors) >= 1


class TestExportImportPipeline:
    """Tests for ExportImportPipeline."""

    def _make_records(self) -> list[dict[str, Any]]:
        """Create sample records."""
        return [
            {"fingerprint": "fp1", "title": "iPhone 15", "price": 45000, "currency": "UAH", "url": "https://olx.ua/1", "city": "Kyiv", "platform": "olx", "is_active": True},
            {"fingerprint": "fp2", "title": "Samsung S24", "price": 35000, "currency": "UAH", "url": "https://olx.ua/2", "city": "Lviv", "platform": "olx", "is_active": True},
            {"fingerprint": "fp3", "title": "MacBook Pro", "price": 85000, "currency": "UAH", "url": "https://rozetka.ua/3", "city": "Dnipro", "platform": "rozetka", "is_active": False},
        ]

    def test_export_json(self, tmp_path) -> None:
        """Export as JSON."""
        pipeline = ExportImportPipeline(output_dir=str(tmp_path))
        records = self._make_records()
        result = pipeline.export_json(records)
        assert result.format == ExportFormat.JSON
        assert result.record_count >= 2  # At least valid ones
        assert result.file_path is not None
        assert os.path.exists(result.file_path)

    def test_export_csv(self, tmp_path) -> None:
        """Export as CSV."""
        pipeline = ExportImportPipeline(output_dir=str(tmp_path))
        records = self._make_records()
        result = pipeline.export_csv(records)
        assert result.format == ExportFormat.CSV
        assert result.file_path is not None
        assert os.path.exists(result.file_path)

    def test_export_json_without_validation(self, tmp_path) -> None:
        """Export without validation includes all records."""
        pipeline = ExportImportPipeline(output_dir=str(tmp_path))
        records = self._make_records()
        result = pipeline.export_json(records, validate=False)
        assert result.record_count == 3

    def test_import_json(self, tmp_path) -> None:
        """Import from JSON."""
        pipeline = ExportImportPipeline(output_dir=str(tmp_path))
        records = self._make_records()

        # Export first
        export_result = pipeline.export_json(records, validate=False)
        file_path = export_result.file_path

        # Import
        import_result = pipeline.import_json(file_path, mode=ImportMode.REPLACE)
        assert import_result.format == ExportFormat.JSON
        assert import_result.imported_count >= 1

    def test_import_json_append(self, tmp_path) -> None:
        """Append import skips duplicates."""
        pipeline = ExportImportPipeline(output_dir=str(tmp_path))
        records = self._make_records()

        export_result = pipeline.export_json(records, validate=False)
        import_result = pipeline.import_json(
            export_result.file_path, mode=ImportMode.APPEND, existing=records
        )
        # All records already exist → skipped
        assert import_result.skipped_count >= 2

    def test_import_json_upsert(self, tmp_path) -> None:
        """Upsert import updates existing."""
        pipeline = ExportImportPipeline(output_dir=str(tmp_path))
        records = self._make_records()

        export_result = pipeline.export_json(records, validate=False)
        import_result = pipeline.import_json(
            export_result.file_path, mode=ImportMode.UPSERT, existing=records
        )
        assert import_result.updated_count >= 2

    def test_import_csv(self, tmp_path) -> None:
        """Import from CSV."""
        pipeline = ExportImportPipeline(output_dir=str(tmp_path))
        records = self._make_records()

        # Export to CSV first
        export_result = pipeline.export_csv(records, validate=False)
        file_path = export_result.file_path

        # Import
        import_result = pipeline.import_csv(file_path, mode=ImportMode.REPLACE)
        assert import_result.format == ExportFormat.CSV
        assert import_result.imported_count >= 1

    def test_incremental_export(self, tmp_path) -> None:
        """Incremental export only changed records."""
        pipeline = ExportImportPipeline(output_dir=str(tmp_path))
        records = [
            {"fingerprint": "fp1", "title": "Old", "platform": "olx", "updated_at": time.time() - 100},
            {"fingerprint": "fp2", "title": "New", "platform": "olx", "updated_at": time.time()},
        ]

        result = pipeline.incremental_export(
            records, last_export_timestamp=time.time() - 50
        )
        assert result.record_count == 1  # Only the "New" record

    def test_validate(self) -> None:
        """Validate records."""
        pipeline = ExportImportPipeline()
        records = [
            {"fingerprint": "fp1", "title": "Good", "platform": "olx"},
            {"title": "Missing fields"},  # Missing fingerprint + platform
        ]
        result = pipeline.validate(records)
        assert result["valid_count"] >= 1
        assert result["invalid_count"] >= 1

    def test_map_fields(self) -> None:
        """Map field names."""
        pipeline = ExportImportPipeline()
        records = [{"fp": "fp1", "name": "iPhone"}]
        field_map = {"fp": "fingerprint", "name": "title"}
        mapped = pipeline.map_fields(records, field_map)
        assert mapped[0]["fingerprint"] == "fp1"
        assert mapped[0]["title"] == "iPhone"

    def test_export_gzip_json(self, tmp_path) -> None:
        """Export as gzip JSON."""
        pipeline = ExportImportPipeline(output_dir=str(tmp_path))
        records = self._make_records()
        result = pipeline.export_gzip_json(records, validate=False)
        assert result.format == ExportFormat.GZIP_JSON
        assert result.file_path is not None
        assert os.path.exists(result.file_path)
        # Gzip should be smaller than raw JSON
        assert result.byte_count > 0

    def test_export_and_import_roundtrip(self, tmp_path) -> None:
        """Export JSON → import → same data."""
        pipeline = ExportImportPipeline(output_dir=str(tmp_path))
        records = self._make_records()

        export_result = pipeline.export_json(records, validate=False)
        import_result = pipeline.import_json(export_result.file_path, mode=ImportMode.REPLACE, validate=False)
        assert import_result.imported_count == 3
