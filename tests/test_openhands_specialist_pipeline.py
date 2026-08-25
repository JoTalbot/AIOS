from aios_core.openhands import ReviewDecision
from aios_core.openhands.specialist_pipeline import SpecialistResult, SpecialistReviewPipeline, conservative_executor


def test_specialist_pipeline_fails_closed_without_runtime():
    results, meta = SpecialistReviewPipeline(conservative_executor).run("security")
    assert results
    assert meta.decision is ReviewDecision.CHANGES_REQUESTED
    assert all(result.error for result in results)


def test_specialist_pipeline_aggregates_all_approvals():
    def approve(spec, context):
        return SpecialistResult(spec=spec, verdict=ReviewDecision.APPROVED, evidence="verified")

    results, meta = SpecialistReviewPipeline(approve).run("feature")
    assert results
    assert meta.decision is ReviewDecision.APPROVED
    assert meta.blockers == ()


def test_specialist_rejection_blocks_meta_review():
    def reject_one(spec, context):
        verdict = ReviewDecision.CHANGES_REQUESTED if spec.name == "security" else ReviewDecision.APPROVED
        return SpecialistResult(spec=spec, verdict=verdict)

    _, meta = SpecialistReviewPipeline(reject_one).run("security")
    assert meta.decision is ReviewDecision.CHANGES_REQUESTED
