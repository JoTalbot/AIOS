import pytest
from aios_core.workflow import WorkflowEngine, WorkflowStep

def fail_action(**kwargs):
    raise ValueError("Network timeout")

def heal_action(error, **kwargs):
    # Fix the issue by using a mock fallback
    return {"data": "fallback_data", "recovered_from": error}

def test_dag_self_healing():
    engine = WorkflowEngine()
    wf = engine.create_workflow("heal_test")
    
    step1 = WorkflowStep(
        id="step1",
        name="fetch",
        action=fail_action,
        is_self_healing=True,
        healing_action=heal_action
    )
    
    def step2_action(step1_result, **kwargs):
        assert step1_result["data"] == "fallback_data"
        return "success"
        
    step2 = WorkflowStep(
        id="step2",
        name="process",
        action=step2_action,
        depends_on=["step1"]
    )
    
    wf.add_step(step1)
    wf.add_step(step2)
    
    result = engine.execute(wf.id)
    
    assert result["status"] == "completed"
    assert result["step_results"]["step1"]["data"] == "fallback_data"
    assert result["step_results"]["step2"] == "success"
