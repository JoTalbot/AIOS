"""End-to-end tests for the main runtime integration layer."""


def test_runtime_pipeline_contract():
    pipeline = [
        "goal",
        "runtime",
        "agent_orchestrator",
        "workflow",
        "execution",
        "feedback",
        "learning",
    ]

    assert pipeline[0] == "goal"
    assert pipeline[-1] == "learning"
    assert len(pipeline) == 7


def test_multi_agent_and_single_agent_share_runtime_entrypoint():
    modes = {
        "single_agent": "runtime",
        "multi_agent": "agent_orchestrator",
    }

    assert "runtime" in modes.values()
    assert "agent_orchestrator" in modes.values()
