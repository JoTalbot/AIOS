from aios_core.runtime import AgentResult, AgentStatus, AgentTask


def test_agent_task_has_stable_execution_contract():
    task = AgentTask(id="t1", goal="implement feature", task_type="feature")
    assert task.id == "t1"
    assert task.task_type == "feature"
    assert task.required_gates == ()


def test_agent_result_carries_evidence_and_verdict():
    result = AgentResult(
        task_id="t1",
        status=AgentStatus.COMPLETED,
        evidence=("tests passed",),
        verdict="APPROVED",
    )
    assert result.status is AgentStatus.COMPLETED
    assert result.evidence == ("tests passed",)
    assert result.verdict == "APPROVED"
