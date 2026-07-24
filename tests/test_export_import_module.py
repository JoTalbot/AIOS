"""Tests for aios_core/export_import_pipeline.py"""
from __future__ import annotations
import pytest
from aios_core.export_import_pipeline import ExportImportPipeline, ExportSchema


@pytest.fixture()
def pipeline(tmp_path):
    schema = ExportSchema(fields=[{"name": "id"}, {"name": "name"}], primary_key="id")
    return ExportImportPipeline(schema=schema, output_dir=str(tmp_path))


class TestExportSchema:
    def test_create(self):
        s = ExportSchema(fields=[{"name": "id"}], primary_key="id")
        assert isinstance(s.fields, list)

    def test_validate_record(self):
        s = ExportSchema(fields=[{"name": "id"}, {"name": "name"}], primary_key="id")
        result = s.validate_record({"id": "1", "name": "test"})
        assert isinstance(result, (bool, dict, list))


class TestExportImportPipeline:
    def test_export_json(self, pipeline):
        records = [{"id": "1", "name": "A"}, {"id": "2", "name": "B"}]
        result = pipeline.export_json(records, "test.json")
        assert result is not None

    def test_export_csv(self, pipeline):
        records = [{"id": "1", "name": "A"}]
        result = pipeline.export_csv(records, "test.csv")
        assert result is not None

    def test_validate(self, pipeline):
        records = [{"id": "1", "name": "A"}, {"id": "2", "name": "B"}]
        result = pipeline.validate(records)
        assert isinstance(result, dict)
        assert result["valid_count"] == 2

    def test_stats(self, pipeline):
        assert pipeline.schema is not None
