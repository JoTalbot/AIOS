"""CI tests for the deterministic OpenHands evaluation suite."""

from aios_core.openhands.evaluation_suite import run_prompt_evaluation


def test_all_prompt_evaluation_scenarios_pass():
    results = run_prompt_evaluation()
    assert results
    assert all(results.values()), results
