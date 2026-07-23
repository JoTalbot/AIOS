"""Knowledge distillation full."""
from aios_core.knowledge_distillation import KnowledgeDistillation
def test(): s=KnowledgeDistillation().stats(); assert isinstance(s,dict)
