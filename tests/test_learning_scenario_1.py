"""Learning scenario test."""
from aios_core.active_learning import ActiveLearner

def test_pipeline():
    learner = ActiveLearner()
    for i in range(10):
        learner.add_unlabeled({'id': i})
    assert learner.stats()['unlabeled'] == 10

def test_label():
    learner = ActiveLearner()
    learner.add_unlabeled({'id': 1})
    item = learner.query()
    learner.label(item, 'pos')
    assert learner.stats()['labeled'] == 1
