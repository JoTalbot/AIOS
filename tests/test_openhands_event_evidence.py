from aios_core.openhands.event_evidence import build_completion_report


def test_event_evidence_is_conservative():
    report = build_completion_report(
        {
            "events": [
                {"type": "command_run", "command": "pytest tests/x.py", "result": "exit code 0"},
                {"type": "test_result", "result": "3 passed"},
                {"type": "diff_check", "result": "clean"},
            ]
        },
        "reviewer",
    )
    assert len(report.evidence) == 3
    assert report.evidence_passed()


def test_unknown_or_empty_events_do_not_create_success_evidence():
    report = build_completion_report({"events": [{"type": "message", "text": "looks good"}]}, "reviewer")
    assert report.evidence == []
    assert not report.evidence_passed()
