"""Full platform infrastructure tests."""

from aios_core.platforms.catalog import PlatformCatalog
from aios_core.platforms.scaffold import PlatformScaffolder
from aios_core.platforms.apkfetch import ApkFetcher
from aios_core.platforms.fleet import FleetManager
from aios_core.platforms.shardexec import ShardExecutor


def test_catalog_init():
    pc = PlatformCatalog()
    assert pc is not None


def test_scaffolder_init():
    ps = PlatformScaffolder()
    assert ps is not None


def test_apk_fetcher_init():
    af = ApkFetcher()
    assert af is not None


def test_fleet_manager_init():
    fm = FleetManager()
    assert fm is not None


def test_shard_executor_init():
    se = ShardExecutor()
    assert se is not None
