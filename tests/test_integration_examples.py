"""Tests for integration examples and enhanced integration."""

from aios_core.integration_examples import ExampleRunner


def test_example_runner_init():
    er = ExampleRunner()
    assert er is not None
