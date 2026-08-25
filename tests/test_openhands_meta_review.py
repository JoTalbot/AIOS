from aios_core.openhands import ReviewDecision, SpecialistVerdict, aggregate_verdicts


def test_meta_review_fails_closed_on_rejection():
    result = aggregate_verdicts((
        SpecialistVerdict("security", ReviewDecision.APPROVED),
        SpecialistVerdict("tests", ReviewDecision.CHANGES_REQUESTED),
    ))
    assert result.decision is ReviewDecision.CHANGES_REQUESTED
    assert result.blockers == ("tests",)


def test_meta_review_requires_specialists():
    result = aggregate_verdicts(())
    assert result.decision is ReviewDecision.CHANGES_REQUESTED
    assert "no specialist verdicts" in result.blockers


def test_meta_review_approves_only_when_all_approve():
    result = aggregate_verdicts((
        SpecialistVerdict("architecture", ReviewDecision.APPROVED),
        SpecialistVerdict("security", ReviewDecision.APPROVED),
    ))
    assert result.decision is ReviewDecision.APPROVED
    assert result.blockers == ()
