"""Tests for aios_core/android_test_generator.py"""
from __future__ import annotations
import pytest
from aios_core.android_test_generator import AndroidTestGenerator


@pytest.fixture()
def generator(tmp_path):
    return AndroidTestGenerator(output_dir=str(tmp_path))


class TestAndroidTestGenerator:
    def test_create(self, generator):
        assert generator is not None

    def test_from_user_flow(self, generator):
        flow = ["tap:search_button", "type:search_field:iPhone", "tap:result_item"]
        result = generator.from_user_flow(flow, platform="olx", name="search_flow")
        assert result is not None

    def test_save_test(self, generator):
        flow = ["tap:btn"]
        test = generator.from_user_flow(flow, platform="olx", name="simple")
        if test:
            generator.save_test(test)

    def test_list_generated(self, generator):
        result = generator.list_generated()
        assert isinstance(result, list)
