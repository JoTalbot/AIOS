"""Tests for aios_core/enhanced_logging.py"""
from __future__ import annotations
import pytest
from aios_core.enhanced_logging import EnhancedLogger, LogConfig, CorrelationContext


@pytest.fixture()
def logger():
    return EnhancedLogger(config=LogConfig())


class TestCorrelationContext:
    def test_create(self):
        ctx = CorrelationContext()
        assert ctx is not None

    def test_set_correlation_id(self):
        ctx = CorrelationContext()
        ctx.set_correlation_id("corr-123")

    def test_to_dict(self):
        ctx = CorrelationContext()
        ctx.set_correlation_id("corr-123")
        d = ctx.to_dict()
        assert isinstance(d, dict)


class TestEnhancedLogger:
    def test_create(self, logger):
        assert logger is not None

    def test_info(self, logger):
        logger.info("Test message")

    def test_warning(self, logger):
        logger.warning("Warning message")

    def test_error(self, logger):
        logger.error("Error message")

    def test_set_correlation_id(self, logger):
        logger.set_correlation_id("corr-456")

    def test_log_with_context(self, logger):
        logger.set_correlation_id("corr-789")
        logger.log_with_context(level="INFO", message="contextual")

    def test_get_performance_stats(self, logger):
        logger.track_operation("test_op")
        s = logger.get_performance_stats("test_op")
        assert isinstance(s, dict)
