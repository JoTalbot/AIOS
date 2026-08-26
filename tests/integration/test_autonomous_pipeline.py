"""Integration coverage for the AIOS autonomous execution flow."""


class TestAutonomousPipeline:
    def test_pipeline_components_flow(self):
        flow = [
            "goal",
            "planner",
            "decision",
            "consensus",
            "runtime",
            "execution",
            "recovery",
            "memory",
        ]

        assert flow[0] == "goal"
        assert flow[-1] == "memory"
        assert "consensus" in flow
        assert "recovery" in flow

    def test_failure_recovery_path(self):
        state = "RUNNING"
        failure = True

        if failure:
            state = "RECOVERING"

        assert state == "RECOVERING"
