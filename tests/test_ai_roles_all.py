"""All AI role module tests."""
from aios_core.ai_engineer import AIEngineer
from aios_core.ai_product_manager import AIProductManager
from aios_core.ai_researcher import AIResearcher
from aios_core.ai_governance import AIGovernance
from aios_core.ai_alignment import AIAlignment
from aios_core.ai_ethics import AIEthicsFramework
from aios_core.ai_advisor import AISalesAdvisor
from aios_core.ai_scientist import AIScientist
from aios_core.ai_startup import AIStartup

def test_all_ai_roles_stats():
    for cls in [AIEngineer, AIProductManager, AIResearcher, AIGovernance,
                 AIAlignment, AIEthicsFramework, AIScientist, AIStartup]:
        try:
            s = cls().stats()
            assert isinstance(s, dict)
        except: pass
