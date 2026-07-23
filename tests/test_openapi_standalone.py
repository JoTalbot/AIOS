"""OpenAPI standalone test."""
from aios_core.openapi import OpenAPIGenerator
def test_init(): assert OpenAPIGenerator() is not None
