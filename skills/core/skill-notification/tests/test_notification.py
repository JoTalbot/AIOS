#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/code")
from notification import notify, log_to_journal

def test_log():
    result = log_to_journal("Test journal entry", "info")
    assert "timestamp" in result
    print("Journal log: OK")

def test_notify_log_only():
    result = notify("Test notification", level="info", channel="log")
    assert result.get("logged") == True
    print("Notify (log only): OK")

if __name__ == "__main__":
    test_log()
    test_notify_log_only()
    print("All tests passed!")
