"""ML training deep scenario."""
from aios_core.bayesian import BayesianInference
from aios_core.transfer_learning import TransferLearner
from aios_core.meta_learning import MetaLearner
from aios_core.knowledge_distillation import KnowledgeDistillation
from aios_core.self_supervised import SelfSupervisedLearner
from aios_core.continual_learning import ContinualLearner
from aios_core.curriculum_learning import CurriculumLearner

def test_ml_training_stack():
    for cls in [BayesianInference, TransferLearner, MetaLearner,
                KnowledgeDistillation, SelfSupervisedLearner,
                ContinualLearner, CurriculumLearner]:
        s = cls().stats()
        assert isinstance(s, dict)
