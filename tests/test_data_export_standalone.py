"""Data export standalone test."""
from aios_core.data_export import DataExporter
def test_init(): assert DataExporter(":memory:") is not None
