#!/usr/bin/env python3
"""Тест skill-health-monitor"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/code")
from health_monitor import run_health_check, compute_health_score, grade_from_score

def test_health_check():
    report = run_health_check()
    assert "score" in report
    assert "grade" in report
    assert "disk" in report
    assert 0 <= report["score"] <= 1000
    print(f"Health Score: {report['score']} ({report['grade']})")
    print(f"Status: {report['status']}")

def test_score_grades():
    assert grade_from_score(1000) == "S"
    assert grade_from_score(950) == "A"
    assert grade_from_score(750) == "B"
    assert grade_from_score(100) == "F"

if __name__ == "__main__":
    test_health_check()
    test_score_grades()
    print("All tests passed!")
