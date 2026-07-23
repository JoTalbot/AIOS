"""Final batch tests for remaining utility modules."""

from aios_core.event_store import EventStore
from aios_core.reporter import ReportGenerator
from aios_core.models import ModelManager
from aios_core.openapi import OpenAPIGenerator


def test_event_store_init():
    es = EventStore()
    assert es is not None


def test_report_generator_init():
    rg = ReportGenerator()
    assert rg is not None


def test_model_manager_init():
    mm = ModelManager()
    assert mm is not None


def test_openapi_generator_init():
    og = OpenAPIGenerator()
    assert og is not None
