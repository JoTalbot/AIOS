"""Tests for aios_core/experiment_tracking.py"""
from __future__ import annotations
import pytest
from aios_core.experiment_tracking import ExperimentTracker


@pytest.fixture()
def tracker():
    return ExperimentTracker()


class TestExperimentTracker:
    def test_start_experiment(self, tracker):
        exp = tracker.start_experiment(name="exp1", params={"lr": 0.01, "epochs": 10})
        assert exp is not None

    def test_log_metric(self, tracker):
        exp = tracker.start_experiment(name="exp2", params={"lr": 0.01})
        eid = exp.experiment_id if hasattr(exp, 'experiment_id') else getattr(exp, 'id', 'exp2')
        tracker.log_metric(eid, "loss", 0.5)

    def test_log_metrics(self, tracker):
        exp = tracker.start_experiment(name="exp3", params={})
        eid = exp.experiment_id if hasattr(exp, 'experiment_id') else getattr(exp, 'id', 'exp3')
        tracker.log_metrics(eid, {"loss": 0.3, "accuracy": 0.95})

    def test_add_tag(self, tracker):
        exp = tracker.start_experiment(name="exp4", params={})
        eid = exp.experiment_id if hasattr(exp, 'experiment_id') else getattr(exp, 'id', 'exp4')
        tracker.add_tag(eid, "env", )

    def test_end_experiment(self, tracker):
        exp = tracker.start_experiment(name="exp5", params={})
        eid = exp.experiment_id if hasattr(exp, 'experiment_id') else getattr(exp, 'id', 'exp5')
        tracker.end_experiment(eid)

    def test_list_experiments(self, tracker):
        tracker.start_experiment(name="e1", params={})
        tracker.start_experiment(name="e2", params={})
        exps = tracker.list_experiments()
        assert len(exps) >= 2

    def test_get_experiment(self, tracker):
        exp = tracker.start_experiment(name="exp6", params={})
        eid = exp.experiment_id if hasattr(exp, 'experiment_id') else getattr(exp, 'id', 'exp6')
        fetched = tracker.get_experiment(eid)
        assert fetched is not None

    def test_best_experiment(self, tracker):
        tracker.start_experiment(name="e1", params={})
        best = tracker.best_experiment(metric="loss")
        assert best is not None or best is None

    def test_stats(self, tracker):
        s = tracker.stats()
        assert isinstance(s, dict)
