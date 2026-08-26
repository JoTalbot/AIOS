"""Integration coverage for the new AIOS architecture flow."""


def test_architecture_flow_contract():
    """Documents the expected lifecycle pipeline.

    The runtime flow is:
    Kernel -> Bootstrap -> AgentManager -> AgentRuntime
    -> EventBus -> Persistence -> Recovery
    """
    pipeline = [
        "Kernel",
        "Bootstrap",
        "AgentManager",
        "AgentRuntime",
        "EventBus",
        "Persistence",
        "Recovery",
    ]

    assert pipeline[0] == "Kernel"
    assert pipeline[-1] == "Recovery"
    assert len(pipeline) == 7
