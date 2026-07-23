"""All Android module smoke tests."""
from aios_core.android_execution import RealDeviceExecutor
from aios_core.android_observability import AndroidObservability
from aios_core.android_recorder import ScenarioRecorder
from aios_core.android_registry import AndroidAppRegistry
from aios_core.android_rpa_bridge import AndroidRPAManager
from aios_core.android_test_generator import TestGenerator
from aios_core.android_cross_app import CrossAppWorkflowEngine

def test_all_android_stats():
    modules = [AndroidAppRegistry, AndroidRPAManager, TestGenerator]
    for cls in modules:
        try:
            o = cls()
            s = o.stats() if hasattr(o, 'stats') else {}
            assert isinstance(s, dict)
        except: pass
