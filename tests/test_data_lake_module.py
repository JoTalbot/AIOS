"""Tests for aios_core/data_lake.py"""
from __future__ import annotations
import pytest
from aios_core.data_lake import DataLake


@pytest.fixture()
def lake():
    return DataLake()


class TestDataLake:
    def test_ingest(self, lake):
        lake.ingest({"id": "1", "name": "test", "value": 42.0})

    def test_ingest_batch(self, lake):
        lake.ingest_batch([{"id": "1", "value": 10.0}, {"id": "2", "value": 20.0}])

    def test_query(self, lake):
        lake.ingest({"id": "1", "name": "test"})
        result = lake.query()
        assert isinstance(result, list)

    def test_query_by_field(self, lake):
        lake.ingest({"id": "1", "status": "active"})
        result = lake.query_by_field(field="status", value="active")
        assert isinstance(result, list)

    def test_aggregate(self, lake):
        lake.ingest({"id": "1", "value": 10.0})
        result = lake.aggregate(field="value", operation="sum")
        assert isinstance(result, (int, float, dict))

    def test_create_view(self, lake):
        lake.create_view("my_view")

    def test_stats(self, lake):
        s = lake.stats()
        assert isinstance(s, dict)
