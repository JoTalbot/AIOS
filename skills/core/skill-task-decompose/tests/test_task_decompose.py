#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/code")
from task_decompose import decompose, classify_task, VECTORS_PRIORITY

def test_classify():
    assert classify_task("fix health SLO") == "health_fix"
    assert classify_task("implement new skill") == "skill_implement"
    assert classify_task("check memory durability") == "memory_check"
    assert classify_task("scale free nodes") == "scale_free"
    assert classify_task("clean up stubs") == "cleanup"
    print("Classification: OK")

def test_decompose():
    plan = decompose("Fix SLO and health issues")
    assert "steps" in plan
    assert len(plan["steps"]) > 0
    assert plan["vector"] == "live"
    assert plan["vector_priority"] >= 7
    print(f"Decompose: {len(plan['steps'])} steps, vector={plan['vector']}")

if __name__ == "__main__":
    test_classify()
    test_decompose()
    print("All tests passed!")
