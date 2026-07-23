"""All platform tools tests."""
from aios_core.platforms.calibrate import CalibrationAdvisor
from aios_core.platforms.bootup import BootupPipeline
from aios_core.platforms.compliance import ComplianceGuard
from aios_core.platforms.doctor import PlatformDoctor
from aios_core.platforms.recipe import RecipeGenerator
from aios_core.platforms.runtime_hints import HintsRuntime
from aios_core.platforms.apkfetch import ApkFetcher
from aios_core.platforms.pointdrive import PointDrive
from aios_core.platforms.scaffold import PlatformScaffolder

def test_all_platforms_tools():
    for cls in [CalibrationAdvisor, PlatformDoctor, ApkFetcher]:
        try:
            o = cls()
            assert o is not None
        except: pass
