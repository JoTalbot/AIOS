"""Tests for v9.7.0 CLI subcommands — cross-platform, advisor-v2, search, benchmarks."""

from __future__ import annotations

import argparse

from aios_cli.cross_platform import _add_cross_platform_parsers


def test_cli_cross_platform_subparsers():
    """cross-platform subcommand tree is registered."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    _add_cross_platform_parsers(subparsers)

    # compare
    args = parser.parse_args(["cross-platform", "compare", "--olx-db", ":memory:", "--rozetka-db", ":memory:"])
    assert args.cp_command == "compare"

    # product
    args = parser.parse_args(["cross-platform", "product", "--fingerprint", "fp1", "--platform", "olx"])
    assert args.cp_command == "product"
    assert args.fingerprint == "fp1"

    # arbitrage
    args = parser.parse_args(["cross-platform", "arbitrage", "--min-spread", "15", "--olx-db", ":memory:"])
    assert args.cp_command == "arbitrage"
    assert args.min_spread == 15.0


def test_cli_advisor_v2_subparsers():
    """advisor-v2 subcommand tree is registered."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    _add_cross_platform_parsers(subparsers)

    # recommend
    args = parser.parse_args(["advisor-v2", "recommend", "--title", "iPhone 16"])
    assert args.advisor_v2_command == "recommend"
    assert args.title == "iPhone 16"

    # predict
    args = parser.parse_args(["advisor-v2", "predict", "--fingerprint", "fp1", "--platform", "olx", "--horizon", "14"])
    assert args.advisor_v2_command == "predict"
    assert args.horizon == 14

    # analyze
    args = parser.parse_args(["advisor-v2", "analyze", "--title", "Phone", "--platform", "rozetka"])
    assert args.advisor_v2_command == "analyze"


def test_cli_search_subparsers():
    """search subcommand tree is registered."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    _add_cross_platform_parsers(subparsers)

    # query
    args = parser.parse_args(["search", "query", "--text", "iPhone", "--platform", "olx"])
    assert args.search_command == "query"
    assert args.text == "iPhone"

    # similar
    args = parser.parse_args(["search", "similar", "--fingerprint", "fp1", "--platform", "olx"])
    assert args.search_command == "similar"


def test_cli_benchmarks_subparsers():
    """benchmarks subcommand tree is registered."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    _add_cross_platform_parsers(subparsers)

    # list
    args = parser.parse_args(["benchmarks", "list"])
    assert args.benchmarks_command == "list"

    # check
    args = parser.parse_args(["benchmarks", "check", "--name", "core_import", "--actual-ms", "450"])
    assert args.benchmarks_command == "check"
    assert args.name == "core_import"
    assert args.actual_ms == 450.0
