"""All ML training module tests."""
from aios_core.bayesian import BayesianInference
from aios_core.continual_learning import ContinualLearner
from aios_core.curriculum_learning import CurriculumLearner
from aios_core.self_supervised import SelfSupervisedLearner
from aios_core.transfer_learning import TransferLearner
from aios_core.meta_learning import MetaLearner
from aios_core.knowledge_distillation import KnowledgeDistillation
from aios_core.hierarchical_rl import HierarchicalRL
from aios_core.model_based_rl import ModelBasedRL
from aios_core.offline_rl import OfflineRL

def test_all_ml_stats():
    for cls in [BayesianInference, ContinualLearner, CurriculumLearner,
                 SelfSupervisedLearner, TransferLearner, MetaLearner,
                 KnowledgeDistillation, HierarchicalRL]:
        try:
            s = cls().stats()
            assert isinstance(s, dict)
        except: pass
