"""Tests for platform scaffolding, fleet ensure_device and PoolMonitor."""

import json
import sys

import pytest

from aios_core.platforms import DevicePool, PoolMonitor, Profile, ProfileStore
from aios_core.platforms import descriptor as descriptor_mod
from aios_core.platforms import ensure_device, get_platform, load_catalog_file, scaffold_platform

# ---------------------------------------------------------------------------
# scaffold_platform
# ---------------------------------------------------------------------------


def test_scaffold_dry_run_writes_nothing(tmp_path):
    files = scaffold_platform(
        "demo-market",
        "ua.demo.market",
        project_root=tmp_path,
        dry_run=True,
    )
    assert len(files) == 4
    assert not any(p.exists() for p in tmp_path.rglob("*") if p.is_file())
    yaml_path = next(p for p in files if p.endswith(".yaml"))
    assert "demo-market" in files[yaml_path]
    assert "ua.demo.market" in files[yaml_path]


def test_scaffold_validation_errors(tmp_path):
    with pytest.raises(ValueError):
        scaffold_platform("Bad_Name", "ua.demo", project_root=tmp_path)
    with pytest.raises(ValueError):
        scaffold_platform("demo", "not a package", project_root=tmp_path)
    scaffold_platform("demo", "ua.demo.app", project_root=tmp_path)
    with pytest.raises(ValueError) as exc:
        scaffold_platform("demo", "ua.demo.app", project_root=tmp_path)
    assert "already exists" in str(exc.value)


def test_scaffolded_module_imports_and_yaml_registers(tmp_path, monkeypatch):
    scaffold_platform(
        "test-market",
        "ua.test.market",
        project_root=tmp_path,
        description="scaffolded in test",
    )
    module_dir = tmp_path / "aios_core" / "modules" / "test_market"
    assert (module_dir / "__init__.py").exists()
    assert (module_dir / "storage.py").exists()
    assert (tmp_path / "tests" / "test_test_market_agent.py").exists()

    # Сгенерированный модуль импортируется и хранилище работает:
    # расширяем __path__ пакета aios_core.modules на tmp-корень.
    import aios_core.modules as modules_pkg

    extra_path = str(tmp_path / "aios_core" / "modules")
    modules_pkg.__path__.append(extra_path)
    try:
        sys.modules.pop("aios_core.modules.test_market", None)
        sys.modules.pop("aios_core.modules.test_market.storage", None)
        from aios_core.modules.test_market import TestMarketStorage

        storage = TestMarketStorage(":memory:")
        assert storage.get_ads() == []
        storage.close()

        # Сгенерированный YAML регистрирует платформу с рабочими фабриками.
        try:
            load_catalog_file(tmp_path / "platforms" / "test-market.yaml")
            descriptor = get_platform("test-market")
            assert descriptor.android_package == "ua.test.market"
            assert descriptor.agent_module == "aios_core.modules.test_market"
            opened = descriptor.make_storage(":memory:")
            assert isinstance(opened, TestMarketStorage)
            opened.close()
            adb = descriptor.make_adb(serial="emulator-1")
            assert adb.serial == "emulator-1"
            assert adb.package == "ua.test.market"
        finally:
            descriptor_mod._PLATFORMS.pop("test-market", None)
    finally:
        modules_pkg.__path__.remove(extra_path)
        sys.modules.pop("aios_core.modules.test_market", None)
        sys.modules.pop("aios_core.modules.test_market.storage", None)


def test_scaffold_class_and_module_naming():
    files = scaffold_platform(
        "prom-ua",
        "ua.prom.app",
        project_root="/nonexistent-root",
        dry_run=True,
    )
    storage_py = next(p for p in files if p.endswith("storage.py"))
    assert "class PromUaStorage" in files[storage_py]
    assert "prom_ua" in storage_py


# ---------------------------------------------------------------------------
# ensure_device (bootstrap × pool)
# ---------------------------------------------------------------------------


def test_ensure_device_prefers_pool_lease():
    calls = []
    with DevicePool(":memory:") as pool:
        pool.register("emulator-5556")
        record = ensure_device(
            "olx:work",
            pool=pool,
            create_avd=lambda name: calls.append(("create", name)) or True,
            start_emulator=lambda name: calls.append(("start", name)),
            wait_serial=lambda known: calls.append(("wait", known)) or "emulator-9999",
            list_devices=lambda: [],
        )
        assert record["serial"] == "emulator-5556"
        assert record["profile_key"] == "olx:work"
        assert calls == []  # bootstrap не понадобился


def test_ensure_device_creates_avd_when_pool_empty():
    calls = []
    with DevicePool(":memory:") as pool:
        record = ensure_device(
            "olx:work",
            pool=pool,
            create_avd=lambda name: calls.append(("create", name)) or True,
            start_emulator=lambda name: calls.append(("start", name)),
            wait_serial=lambda known: "emulator-5560",
            list_devices=lambda: ["emulator-5554"],
        )
        assert record is not None
        assert record["serial"] == "emulator-5560"
        assert record["avd_name"] == "aios-olx-work"
        assert pool.device_for("olx:work")["serial"] == "emulator-5560"
    assert ("create", "aios-olx-work") in calls
    assert ("start", "aios-olx-work") in calls
    assert calls[0][0] == "create" and calls[1][0] == "start"


def test_ensure_device_failure_paths():
    with DevicePool(":memory:") as pool:
        # create_avd упал → None, устройство не регистрировалось.
        assert (
            ensure_device(
                "olx:a",
                pool=pool,
                create_avd=lambda n: False,
                start_emulator=lambda n: None,
                wait_serial=lambda k: "emulator-1",
                list_devices=lambda: [],
            )
            is None
        )
        assert pool.status() == []
        # эмулятор не поднялся → None.
        assert (
            ensure_device(
                "olx:b",
                pool=pool,
                create_avd=lambda n: True,
                start_emulator=lambda n: None,
                wait_serial=lambda k: None,
                list_devices=lambda: [],
            )
            is None
        )


def test_ensure_device_syncs_profile_store(tmp_path):
    with ProfileStore(tmp_path / "profiles.sqlite") as store:
        store.add(Profile(platform="olx", name="work"))
        with DevicePool(":memory:") as pool:
            pool.register("emulator-5556")
            ensure_device("olx:work", pool=pool, profile_store=store, list_devices=lambda: [])
            assert store.get("olx", "work").device_serial == "emulator-5556"


# ---------------------------------------------------------------------------
# PoolMonitor
# ---------------------------------------------------------------------------


def test_pool_monitor_run_once_heartbeats_and_reap():
    with DevicePool(":memory:") as pool:
        pool.register("emulator-5556")
        pool.register("emulator-5558")
        # emulator-5558 молчит с давних пор.
        with pool._lock, pool._conn:
            pool._conn.execute(
                "UPDATE devices SET last_heartbeat = '2020-01-01T00:00:00+00:00' "
                "WHERE serial = 'emulator-5558'"
            )
        monitor = PoolMonitor(
            pool=pool,
            probe=lambda: ["emulator-5556"],
            reap_after_s=900,
        )
        report = monitor.run_once()
        assert report["alive_devices"] == 1
        assert report["heartbeats"] == 1
        assert report["reaped"] == ["emulator-5558"]
        assert pool.get("emulator-5558")["status"] == "offline"


def test_pool_monitor_start_stop():
    with DevicePool(":memory:") as pool:
        pool.register("emulator-5556")
        monitor = PoolMonitor(pool=pool, probe=lambda: ["emulator-5556"])
        assert monitor.start(interval_s=0.05) is True
        assert monitor.start(interval_s=0.05) is False  # уже запущен
        import time

        time.sleep(0.15)
        assert monitor.stop() is True
        assert monitor.stop() is False


# ---------------------------------------------------------------------------
# CLI surfaces
# ---------------------------------------------------------------------------


def test_cli_platforms_scaffold_and_list(tmp_path, capsys):
    from aios_cli import main

    main(
        [
            "platforms",
            "scaffold",
            "--name",
            "cli-market",
            "--package",
            "ua.cli.market",
            "--root",
            str(tmp_path),
        ]
    )
    out = json.loads(capsys.readouterr().out)
    assert any(p.endswith("cli-market.yaml") for p in out["written"])
    assert (tmp_path / "aios_core/modules/cli_market/storage.py").exists()

    main(
        [
            "platforms",
            "scaffold",
            "--name",
            "ghost",
            "--package",
            "ua.ghost",
            "--root",
            str(tmp_path / "x"),
            "--dry-run",
        ]
    )
    out = json.loads(capsys.readouterr().out)
    assert any(p.endswith("ghost.yaml") for p in out["planned"])
    assert not (tmp_path / "x").exists()

    main(["platforms", "list"])
    platforms = json.loads(capsys.readouterr().out)
    assert any(p["name"] == "olx" for p in platforms)

    # Без подкоманды — обратная совместимость: список.
    main(["platforms"])
    assert json.loads(capsys.readouterr().out)


def test_cli_devices_ensure_and_monitor(tmp_path, monkeypatch, capsys):
    from aios_cli import main

    monkeypatch.setenv("AIOS_DEVICES_DB", str(tmp_path / "devices.sqlite"))
    monkeypatch.setenv("AIOS_PROFILES_DB", str(tmp_path / "profiles.sqlite"))
    ProfileStore.reset_default()
    try:
        main(["devices", "register", "--serial", "emulator-5556", "--avd", "aios-olx-1"])
        json.loads(capsys.readouterr().out)

        main(["devices", "ensure", "--profile", "olx:work"])
        record = json.loads(capsys.readouterr().out)
        assert record["serial"] == "emulator-5556"
        assert record["profile_key"] == "olx:work"

        # Повторный ensure — идемпотентно то же устройство.
        main(["devices", "ensure", "--profile", "olx:work"])
        again = json.loads(capsys.readouterr().out)
        assert again["serial"] == "emulator-5556"

        # monitor --once: без adb вернёт пустой опрос, но JSON валиден.
        main(["devices", "monitor", "--once"])
        report = json.loads(capsys.readouterr().out)
        assert "alive_devices" in report and "reaped" in report
    finally:
        ProfileStore.reset_default()
