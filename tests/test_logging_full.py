"""Logging full tests."""
from aios_core.logging_config import JSONFormatter, setup_logging
def test_formatter():
    f = JSONFormatter()
    record = logging.LogRecord("t", 20, "p", 1, "msg", (), None)
    result = f.format(record)
    assert isinstance(result, str)
import logging
