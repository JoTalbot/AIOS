from dataclasses import dataclass

from aios_core.openhands import (
    AgentRole,
    Gate,
    MetaReview,
    ReviewDecision,
    SpecialistResult,
    SpecialistReviewPipeline,
    SpecialistVerdict,
    TaskExtras,
    aggregate_verdicts,
)


def test_full_gate_lifecycle_can_complete():
    task = TaskExtras(task_id="integration-1", required_gates=frozenset({Gate.TESTS, Gate.REVIEW}))
    task.mark_gate_passed(Gate.TESTS)
    assert not task.gates_satisfied()
    task.mark_gate_passed(Gate.REVIEW)
    assert task.gates_satisfied()


def test_rejected_repair_cycle_is_bounded():
    task = TaskExtras(task_id="repair-1", max_repairs=2)
    assert task.can_repair()
    task.register_repair()
    task.register_repair()
    assert not task.can_repair()


def test_specialist_pipeline_aggregates_real_executor_results():
    def executor(spec, context):
        return SpecialistResult(spec=spec, verdict=ReviewDecision.APPROVED, evidence="verified")

    pipeline = SpecialistReviewPipeline(executor)
    results, meta = pipeline.run("security", "test context")
    assert results
    assert meta.decision is ReviewDecision.APPROVED


def test_specialist_failure_blocks_completion():
    def executor(spec, context):
        return SpecialistResult(spec=spec, verdict=ReviewDecision.CHANGES_REQUESTED, error="failed")

    pipeline = SpecialistReviewPipeline(executor)
    _, meta = pipeline.run("security")
    assert meta.decision is ReviewDecision.CHANGES_REQUESTED
