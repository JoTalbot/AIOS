"""Deep tests for platforms sub-modules."""

from aios_core.platforms.devices import DeviceManager
from aios_core.platforms.recipe import RecipeGenerator
from aios_core.platforms.runtime_hints import HintsRuntime
from aios_core.platforms.fleetsched import FleetScheduler
from aios_core.platforms.reelscout import ReelsScout


def test_device_manager_init():
    dm = DeviceManager()
    assert dm is not None


def test_recipe_generator_init():
    rg = RecipeGenerator()
    assert rg is not None


def test_hints_runtime_init():
    hr = HintsRuntime()
    assert hr is not None


def test_fleet_scheduler_init():
    fs = FleetScheduler()
    assert fs is not None


def test_reels_scout_init():
    rs = ReelsScout()
    assert rs is not None
