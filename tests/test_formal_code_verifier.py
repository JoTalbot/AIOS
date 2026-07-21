"""Tests for Real-Time Formal Code Verification Engine (Horizon 5.0)."""

import pytest
from aios_core.formal_code_verifier import FormalCodeVerifier


def test_formal_verifier_clean_code():
    verifier = FormalCodeVerifier()
    safe_code = """
import math

def calculate_confidence(scores):
    total = sum(scores)
    mean = total / len(scores) if scores else 0.0
    return math.sqrt(mean)
"""
    result = verifier.verify_code(safe_code, preconditions={"scores": "list"})
    assert result["verified"] is True
    assert result["safety_score"] == 1.0
    assert len(result["detected_violations"]) == 0
    assert len(result["proven_guarantees"]) >= 3


def test_formal_verifier_forbidden_imports():
    verifier = FormalCodeVerifier()
    dangerous_code = """
import os
import subprocess

def execute_cmd(cmd):
    return subprocess.check_output(cmd)
"""
    result = verifier.verify_code(dangerous_code)
    assert result["verified"] is False
    assert result["safety_score"] < 1.0
    assert any("Forbidden module import" in v for v in result["detected_violations"])


def test_formal_verifier_eval_exec_calls():
    verifier = FormalCodeVerifier()
    code_eval = "out = eval('1 + 1')"
    result = verifier.verify_code(code_eval)

    assert result["verified"] is False
    assert any("eval()" in v for v in result["detected_violations"])


def test_formal_verifier_dunder_reflection():
    verifier = FormalCodeVerifier()
    code_dunder = "subclasses = object.__subclasses__()"
    result = verifier.verify_code(code_dunder)

    assert result["verified"] is False
    assert any("__subclasses__" in v for v in result["detected_violations"])


def test_formal_verifier_infinite_loop():
    verifier = FormalCodeVerifier()
    infinite_loop_code = """
def infinite_spin():
    x = 0
    while True:
        x += 1
"""
    result = verifier.verify_code(infinite_loop_code)
    assert result["verified"] is False
    assert any("Unbounded infinite while loop" in v for v in result["detected_violations"])


def test_formal_verifier_syntax_error():
    verifier = FormalCodeVerifier()
    invalid_syntax = "def broken_func("
    result = verifier.verify_code(invalid_syntax)

    assert result["verified"] is False
    assert any("Syntax Error" in v for v in result["detected_violations"])
