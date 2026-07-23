"""Data scenario test."""
from aios_core.data_export import DataExporter, DataImporter

def test_exporters():
    assert DataExporter is not None
    assert DataImporter is not None
