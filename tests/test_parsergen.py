"""Tests for parser code generation."""
from aios_core.platforms.parsergen import ParserGenerator
def test_parsergen_init():
    pg = ParserGenerator()
    assert pg is not None
