"""Test fixed enhanced_logging"""

from aios_core.enhanced_logging import (
    LogConfig,
    EnhancedLogger,
    setup_enhanced_logging,
    LogAggregator,
)


def test_log_config_defaults():
    cfg = LogConfig()
    assert cfg.level == "INFO"
    assert cfg.enable_correlation is True


def test_enhanced_logger_creation():
    cfg = LogConfig(log_file="/tmp/test_aios.log", enable_correlation=False)
    logger = EnhancedLogger(cfg)
    assert logger is not None
    assert logger.config.log_file == "/tmp/test_aios.log"


def test_correlation_context():
    cfg = LogConfig(log_file="/tmp/test_aios2.log")
    logger = EnhancedLogger(cfg)
    logger.set_correlation_id("test-123")
    assert logger.correlation_context.correlation_id == "test-123"


def test_performance_tracking():
    cfg = LogConfig(log_file="/tmp/test_aios3.log")
    logger = EnhancedLogger(cfg)
    with logger.track_operation("test_op", table="users") as op_id:
        assert op_id is not None
    stats = logger.get_performance_stats("test_op")
    assert stats["count"] >= 1


def test_log_aggregator_sync():
    cfg = LogConfig(ship_to_external=False)
    agg = LogAggregator(cfg)
    result = agg.ship_logs([{"msg": "test"}])
    assert result is False  # disabled


def test_setup_function():
    logger = setup_enhanced_logging(LogConfig(log_file="/tmp/test_setup.log"))
    assert logger is not None
