import pytest
from aios_core.ai_safety import AISafetyFramework, ConstitutionalSafety

def test_safety_framework_clean_action():
    framework = AISafetyFramework()
    action = {"action": "generate_report", "data": "metrics"}
    
    result = framework.comprehensive_safety_check(action)
    
    assert result["overall_safe"] is True
    assert result["incidents"] == 0
    assert result["average_safety_score"] > 0.8
    assert framework.stats()["checks_performed"] == 1

def test_safety_framework_harmful_action():
    framework = AISafetyFramework()
    # "harm" and "damage" keywords should trigger ConstitutionalSafety
    action = {"action": "execute_command", "intent": "cause harm and damage database"}
    
    result = framework.comprehensive_safety_check(action)
    
    assert result["overall_safe"] is False
    assert result["incidents"] == 1
    assert "constitutional" in result["layer_results"]
    assert result["layer_results"]["constitutional"]["safe"] is False
    assert "non_maleficence" in result["layer_results"]["constitutional"]["violations"]
    
    report = framework.get_safety_report()
    assert report["total_incidents"] == 1
    assert report["recent_incidents"][0]["layer"] == "constitutional"

def test_safety_framework_multiple_violations():
    framework = AISafetyFramework()
    action = {"action": "injure user and damage property", "target": "harm"}
    
    result = framework.comprehensive_safety_check(action)
    assert result["overall_safe"] is False
    # constitutional check should fail, score drops
    assert result["average_safety_score"] < 0.95
