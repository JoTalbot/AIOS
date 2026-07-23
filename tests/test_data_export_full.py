"""Data export full new."""
from aios_core.data_export import DataExporter
def test(): de=DataExporter(":memory:"); assert de is not None
