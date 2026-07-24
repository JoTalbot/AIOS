"""Tests for the platforms/profiles architecture (multi-account,
multi-marketplace): descriptor registry, ProfileStore CRUD, resolver
precedence, storage isolation, CLI and REST surfaces."""

import json

import pytest
import pytest_asyncio

from aios_core.platforms import (
    PlatformDescriptor,
    Profile,
    ProfileStore,
    adb_for,
    get_platform,
    list_platforms,
    register_platform,
    resolve_profile,
    storage_for,
)

# ---------------------------------------------------------------------------
# Descriptor registry
# ---------------------------------------------------------------------------


def test_registry_has_olx_and_lists_sorted():
    names = [d.name for d in list_platforms()]
    assert "olx" in names
    assert names == sorted(names)
    olx = get_platform("olx")
    assert olx.android_package == "ua.slando"
    assert olx.legacy_default_db == "olx_ads.sqlite"
    assert olx.to_dict()["agent_module"] == "aios_core.modules.olx"


def test_unknown_platform_raises_with_known_list():
    with pytest.raises(ValueError) as exc:
        get_platform("no-such-app")
    assert "no-such-app" in str(exc.value)
    assert "olx" in str(exc.value)


def test_register_platform_is_open_closed():
    descriptor = PlatformDescriptor(
        name="demo-market",
        android_package="ua.demo.market",
        agent_module="demo.agent",
        description="test-only descriptor",
    )
    register_platform(descriptor)
    try:
        assert get_platform("demo-market").android_package == "ua.demo.market"
        assert "demo-market" in [d.name for d in list_platforms()]
    finally:
        # Убираем тестовый дескриптор, не мутируя реестр для других тестов.
        from aios_core.platforms import descriptor as descriptor_mod

        descriptor_mod._PLATFORMS.pop("demo-market", None)


def test_profile_key_fingerprint_and_serialization():
    profile = Profile(platform="olx", name="work", device_serial="emulator-5556")
    assert profile.key == "olx:work"
    assert len(profile.fingerprint) == 12
    as_dict = profile.to_dict()
    assert as_dict["key"] == "olx:work"
    assert as_dict["device_serial"] == "emulator-5556"
    assert as_dict["ephemeral"] is False


# ---------------------------------------------------------------------------
# ProfileStore CRUD
# ---------------------------------------------------------------------------


def test_store_crud_and_default_management(tmp_path):
    with ProfileStore(tmp_path / "profiles.sqlite") as store:
        work = store.add(
            Profile(
                platform="olx",
                name="work",
                device_serial="emulator-5556",
                db_path=str(tmp_path / "work.sqlite"),
                is_default=True,
            )
        )
        assert work.is_default is True
        store.add(Profile(platform="olx", name="home", notes="личный"))
        store.add(Profile(platform="other-app", name="main"))

        assert [p.name for p in store.list("olx")] == ["home", "work"]
        assert len(store.list()) == 3
        assert store.get("olx", "home").notes == "личный"
        assert store.get_default("olx").name == "work"

        # Точечное обновление + смена default снимает флаг с остальных.
        updated = store.update("olx", "home", device_serial="emulator-5558")
        assert updated.device_serial == "emulator-5558"
        store.set_default("olx", "home")
        assert store.get_default("olx").name == "home"
        assert store.get("olx", "work").is_default is False

        # Дубликат ключа запрещён.
        with pytest.raises(ValueError):
            store.add(Profile(platform="olx", name="work"))

        assert store.remove("olx", "home") is True
        assert store.remove("olx", "home") is False
        assert store.get_default("olx") is None


# ---------------------------------------------------------------------------
# Resolver precedence
# ---------------------------------------------------------------------------


@pytest.fixture
def store(tmp_path):
    with ProfileStore(tmp_path / "profiles.sqlite") as s:
        s.add(
            Profile(
                platform="olx",
                name="work",
                db_path=str(tmp_path / "work.sqlite"),
            )
        )
        s.add(
            Profile(
                platform="olx",
                name="main",
                db_path=str(tmp_path / "main.sqlite"),
                is_default=True,
            )
        )
        yield s


def test_resolver_explicit_name_beats_env_and_default(store, monkeypatch):
    monkeypatch.setenv("AIOS_PROFILE", "main")
    profile = resolve_profile("olx", "work", store=store)
    assert profile.name == "work"
    profile = resolve_profile("olx", store=store)
    assert profile.name == "main"  # env wins over registry default


def test_resolver_registry_default_then_ephemeral(store, monkeypatch, tmp_path):
    monkeypatch.delenv("AIOS_PROFILE", raising=False)
    assert resolve_profile("olx", store=store).name == "main"

    empty = ProfileStore(":memory:")
    try:
        profile = resolve_profile("olx", store=empty)
        assert profile.ephemeral is True
        assert profile.name == "default"
        # Legacy single-profile path сохранён для обратной совместимости.
        assert profile.db_path == "olx_ads.sqlite"
    finally:
        empty.close()


def test_resolver_unknown_profile_raises(store):
    with pytest.raises(ValueError) as exc:
        resolve_profile("olx", "ghost", store=store)
    assert "olx:ghost" in str(exc.value)


def test_resolver_auto_db_path_under_data_dir(store):
    store.add(Profile(platform="olx", name="auto"))
    profile = resolve_profile("olx", "auto", store=store)
    assert profile.db_path.replace("\\", "/").endswith("data/olx/auto.sqlite")


# ---------------------------------------------------------------------------
# Isolation + device binding
# ---------------------------------------------------------------------------


def test_storage_for_isolates_profiles(store, tmp_path):
    from aios_core.modules.olx import AdCard

    work_storage = storage_for("olx", "work", store=store)
    home_storage = storage_for("olx", "main", store=store)
    try:
        work_storage.save_ads([AdCard(title="Рабочее", url="http://x/1.html")])
        assert len(work_storage.get_ads()) == 1
        assert len(home_storage.get_ads()) == 0
    finally:
        work_storage.close()
        home_storage.close()
    # Файлы действительно разные.
    work_db = tmp_path / "work.sqlite"
    main_db = tmp_path / "main.sqlite"
    assert work_db.exists() and main_db.exists()
    assert work_db != main_db


def test_adb_for_binds_device_serial(store):
    store.update("olx", "work", device_serial="emulator-5556")
    adb = adb_for("olx", "work", store=store)
    assert adb.serial == "emulator-5556"
    assert adb.adb == "adb -s emulator-5556"

    unbound = adb_for("olx", "main", store=store)
    assert unbound.serial is None
    assert unbound.adb == "adb"


def test_adb_controller_scopes_commands_to_serial():
    from aios_core.modules.olx import ADBController

    class SpyADB(ADBController):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.commands = []

        def run(self, command):
            self.commands.append(command)
            return {"code": 0, "stdout": "", "stderr": ""}

    adb = SpyADB(serial="emulator-5556")
    adb.swipe(0, 0, 100, 100)
    adb.tap(10, 20)
    adb.open_app()
    assert all(command.startswith("adb -s emulator-5556") for command in adb.commands)

    plain = SpyADB()
    plain.swipe(0, 0, 1, 1)
    assert plain.commands[0].startswith("adb shell input swipe")


# ---------------------------------------------------------------------------
# CLI surface
# ---------------------------------------------------------------------------


@pytest.fixture
def cli_registry(tmp_path, monkeypatch):
    """Изолированный process-wide реестр профилей для CLI."""
    monkeypatch.setenv("AIOS_PROFILES_DB", str(tmp_path / "profiles.sqlite"))
    ProfileStore.reset_default()
    yield tmp_path
    ProfileStore.reset_default()


def test_cli_profiles_crud_flow(cli_registry, capsys):
    from aios_cli import main

    main(["profiles", "list"])
    assert json.loads(capsys.readouterr().out) == []

    main(
        [
            "profiles",
            "add",
            "--platform",
            "olx",
            "--name",
            "work",
            "--device",
            "emulator-5556",
            "--default",
        ]
    )
    added = json.loads(capsys.readouterr().out)
    assert added["key"] == "olx:work"
    assert added["is_default"] is True

    main(["profiles", "add", "--platform", "olx", "--name", "home"])
    json.loads(capsys.readouterr().out)
    # duplicate → JSON error, no crash
    main(["profiles", "add", "--platform", "olx", "--name", "home"])
    assert "error" in json.loads(capsys.readouterr().out)

    main(["profiles", "show", "--platform", "olx", "--name", "work"])
    assert json.loads(capsys.readouterr().out)["device_serial"] == "emulator-5556"

    main(["profiles", "set-default", "--platform", "olx", "--name", "home"])
    assert json.loads(capsys.readouterr().out)["is_default"] is True

    main(["profiles", "remove", "--platform", "olx", "--name", "home"])
    assert json.loads(capsys.readouterr().out)["removed"] is True

    main(["profiles", "show", "--platform", "olx", "--name", "home"])
    assert "error" in json.loads(capsys.readouterr().out)


def test_cli_platforms_listing(cli_registry, capsys):
    from aios_cli import main

    main(["platforms"])
    platforms = json.loads(capsys.readouterr().out)
    assert any(p["name"] == "olx" for p in platforms)


def test_cli_olx_profile_isolation_and_errors(cli_registry, tmp_path, capsys):
    from aios_cli import main
    from aios_core.modules.olx import AdCard

    work_db = tmp_path / "work.sqlite"
    main(["profiles", "add", "--platform", "olx", "--name", "work", "--db", str(work_db)])
    json.loads(capsys.readouterr().out)

    # Данные в профиле work:
    from aios_core.modules.olx import OLXStorage

    with OLXStorage(work_db) as s:
        s.save_ads([AdCard(title="Только в work", url="http://x/w.html")])

    main(["olx", "stats", "--profile", "work"])
    work_stats = json.loads(capsys.readouterr().out)
    assert work_stats["total_ads"] == 1

    # Другой профиль — пустой, дефолтный легаси-путь не задет.
    main(
        [
            "profiles",
            "add",
            "--platform",
            "olx",
            "--name",
            "home",
            "--db",
            str(tmp_path / "home.sqlite"),
        ]
    )
    json.loads(capsys.readouterr().out)
    main(["olx", "stats", "--profile", "home"])
    assert json.loads(capsys.readouterr().out)["total_ads"] == 0

    # Явный --db обходит реестр профилей.
    other_db = tmp_path / "other.sqlite"
    with OLXStorage(other_db) as s:
        s.save_ads(
            [
                AdCard(title="Через --db", url="http://x/o.html"),
                AdCard(title="Ещё", url="http://x/o2.html"),
            ]
        )
    main(["olx", "stats", "--db", str(other_db)])
    assert json.loads(capsys.readouterr().out)["total_ads"] == 2

    # Неизвестный профиль — чистая JSON-ошибка без traceback.
    main(["olx", "stats", "--profile", "ghost"])
    out = json.loads(capsys.readouterr().out)
    assert "error" in out and "ghost" in out["error"]


# ---------------------------------------------------------------------------
# REST surface
# ---------------------------------------------------------------------------

import os

from httpx import ASGITransport, AsyncClient

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest_asyncio.fixture
async def api_client(tmp_path):
    from aios_core.api.app import AIOSAPI

    store = ProfileStore(":memory:")
    api = AIOSAPI(
        db_path=":memory:",
        constitution_dir=os.path.join(_PROJECT_ROOT, "docs/constitution"),
        policies_dir=os.path.join(_PROJECT_ROOT, "policies"),
        auth_required=False,
        profile_store=store,
    )
    app = api.create_starlette_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, tmp_path
    store.close()


@pytest.mark.asyncio
async def test_rest_platforms_and_profiles_crud(api_client):
    client, tmp_path = api_client

    platforms = await client.get("/api/v1/platforms")
    assert platforms.status_code == 200
    assert any(p["name"] == "olx" for p in platforms.json()["platforms"])

    created = await client.post(
        "/api/v1/profiles",
        json={
            "platform": "olx",
            "name": "work",
            "device_serial": "emulator-5556",
            "db_path": str(tmp_path / "work.sqlite"),
            "is_default": True,
        },
    )
    assert created.status_code == 201
    assert created.json()["key"] == "olx:work"

    listed = await client.get("/api/v1/profiles", params={"platform": "olx"})
    assert [p["name"] for p in listed.json()["profiles"]] == ["work"]

    shown = await client.get("/api/v1/profiles/olx/work")
    assert shown.json()["device_serial"] == "emulator-5556"

    missing = await client.get("/api/v1/profiles/olx/ghost")
    assert missing.status_code == 404

    await client.post(
        "/api/v1/profiles",
        json={
            "platform": "olx",
            "name": "home",
            "db_path": str(tmp_path / "home.sqlite"),
        },
    )
    defaulted = await client.post("/api/v1/profiles/olx/default", json={"name": "home"})
    assert defaulted.json()["is_default"] is True

    removed = await client.delete("/api/v1/profiles/olx/home")
    assert removed.json()["removed"] is True


@pytest.mark.asyncio
async def test_rest_profile_scoped_olx_storage(api_client):
    from aios_core.modules.olx import AdCard, OLXStorage

    client, tmp_path = api_client
    work_db = tmp_path / "work.sqlite"

    await client.post(
        "/api/v1/profiles",
        json={
            "platform": "olx",
            "name": "work",
            "db_path": str(work_db),
        },
    )

    # Сидим объявление напрямую в БД профиля work.
    with OLXStorage(work_db) as seeded:
        seeded.save_ads([AdCard(title="Профильное", url="http://x/p.html")])

    scoped = await client.get("/api/v1/modules/olx/ads", params={"profile": "work"})
    assert scoped.status_code == 200
    assert scoped.json()["total"] == 1

    # Без ?profile — дефолтное хранилище API, данных профиля там нет.
    unscoped = await client.get("/api/v1/modules/olx/ads")
    assert unscoped.json()["total"] == 0

    # own-ads тоже профильно-скопированы: snapshot в work виден только там.
    snapshot = await client.post(
        "/api/v1/modules/olx/own/snapshot?profile=work",
        json={"ads": [{"title": "Моё", "price": 100.0, "ad_id": "p1"}]},
    )
    assert snapshot.status_code == 200
    own_scoped = await client.get("/api/v1/modules/olx/own", params={"profile": "work"})
    assert own_scoped.json()["count"] == 1
    own_default = await client.get("/api/v1/modules/olx/own")
    assert own_default.json()["count"] == 0

    # Неизвестный профиль → 400 от exception handler.
    ghost = await client.get("/api/v1/modules/olx/ads", params={"profile": "ghost"})
    assert ghost.status_code == 400
    assert "ghost" in ghost.json()["error"]


# ---------------------------------------------------------------------------
# DevicePool
# ---------------------------------------------------------------------------

from aios_core.platforms import DevicePool


def test_device_pool_lease_release_cycle():
    with DevicePool(":memory:") as pool:
        pool.register("emulator-5556", avd_name="aios-olx-1")
        pool.register("emulator-5558", avd_name="aios-olx-2")

        # Первый lease берёт наименее недавно использованное устройство.
        first = pool.lease("olx:work")
        assert first["status"] == "busy"
        assert first["profile_key"] == "olx:work"

        second = pool.lease("olx:home")
        assert second["serial"] != first["serial"]

        # Идемпотентность: повторный lease профиля продлевает его же аренду.
        again = pool.lease("olx:work")
        assert again["serial"] == first["serial"]

        # Пул исчерпан.
        assert pool.lease("olx:third") is None

        assert pool.device_for("olx:work")["avd_name"] == "aios-olx-1"
        assert pool.release("olx:work") == first["serial"]
        assert pool.device_for("olx:work") is None

        # Освободившееся устройство снова доступно.
        reloaned = pool.lease("olx:third")
        assert reloaned["serial"] == first["serial"]


def test_device_pool_pinned_serial_and_conflicts():
    with DevicePool(":memory:") as pool:
        pool.register("emulator-5556")
        assert pool.lease("olx:a", serial="emulator-5556")["serial"] == "emulator-5556"
        assert pool.lease("olx:b", serial="emulator-5556") is None  # busy
        with pytest.raises(ValueError):
            pool.lease("olx:c", serial="unknown-device")


def test_device_pool_lease_syncs_profile_store(tmp_path):
    with ProfileStore(tmp_path / "profiles.sqlite") as store:
        store.add(Profile(platform="olx", name="work"))
        with DevicePool(":memory:") as pool:
            pool.register("emulator-5556")
            pool.lease("olx:work", profile_store=store)
            assert store.get("olx", "work").device_serial == "emulator-5556"


def test_device_pool_heartbeat_and_reap():
    with DevicePool(":memory:") as pool:
        pool.register("emulator-5556")
        pool.lease("olx:work")
        assert pool.heartbeat("emulator-5556") is True
        assert pool.heartbeat("ghost") is False

        # Искусственно устаревший heartbeat → offline + аренда снята.
        with pool._lock, pool._conn:
            pool._conn.execute("UPDATE devices SET last_heartbeat = '2020-01-01T00:00:00+00:00'")
        assert pool.reap_stale(max_silence_s=900) == ["emulator-5556"]
        record = pool.get("emulator-5556")
        assert record["status"] == "offline"
        assert record["profile_key"] is None
        assert pool.lease("olx:x", serial="emulator-5556") is None


# ---------------------------------------------------------------------------
# YAML catalog
# ---------------------------------------------------------------------------

from aios_core.platforms import load_catalog, load_catalog_file


def test_catalog_loads_platform_from_yaml(tmp_path):
    catalog_file = tmp_path / "demo.yaml"
    catalog_file.write_text(
        """
name: demo-market
android_package: ua.demo.market
storage_class: aios_core.modules.olx.storage.OLXStorage
adb_class: aios_core.modules.olx.adb.ADBController
default_locale: ru-RU
legacy_default_db: demo.sqlite
description: demo platform from YAML
""",
        encoding="utf-8",
    )
    try:
        loaded = load_catalog_file(catalog_file)
        assert [d.name for d in loaded] == ["demo-market"]
        descriptor = get_platform("demo-market")
        assert descriptor.android_package == "ua.demo.market"
        assert descriptor.default_locale == "ru-RU"
        assert descriptor.agent_module == "aios_core.modules.demo-market"
        # Фабрики собраны по контракту:
        storage = descriptor.make_storage(":memory:")
        from aios_core.modules.olx import OLXStorage

        assert isinstance(storage, OLXStorage)
        adb = descriptor.make_adb(serial="emulator-1")
        assert adb.serial == "emulator-1"
        assert adb.package == "ua.demo.market"
        assert (
            resolve_profile("demo-market", store=ProfileStore(":memory:")).db_path == "demo.sqlite"
        )
    finally:
        from aios_core.platforms import descriptor as descriptor_mod

        descriptor_mod._PLATFORMS.pop("demo-market", None)


def test_catalog_platforms_list_and_missing_fields(tmp_path):
    listing = tmp_path / "multi.yaml"
    listing.write_text(
        "platforms:\n"
        "  - {name: app-one, android_package: ua.one}\n"
        "  - {name: app-two, android_package: ua.two}\n",
        encoding="utf-8",
    )
    from aios_core.platforms import descriptor as descriptor_mod

    try:
        loaded = load_catalog_file(listing)
        assert [d.name for d in loaded] == ["app-one", "app-two"]
        assert descriptor_mod.get_platform("app-one").storage_factory is None
    finally:
        descriptor_mod._PLATFORMS.pop("app-one", None)
        descriptor_mod._PLATFORMS.pop("app-two", None)

    broken = tmp_path / "broken.yaml"
    broken.write_text("android_package: ua.nope\n", encoding="utf-8")
    with pytest.raises(ValueError) as exc:
        load_catalog_file(broken)
    assert "name" in str(exc.value)


def test_repo_catalog_olx_yaml_matches_builtin():
    loaded = load_catalog("platforms")
    assert any(d.name == "olx" for d in loaded)
    descriptor = get_platform("olx")
    assert descriptor.android_package == "ua.slando"
    assert descriptor.legacy_default_db == "olx_ads.sqlite"
    storage = descriptor.make_storage(":memory:")
    from aios_core.modules.olx import OLXStorage

    assert isinstance(storage, OLXStorage)
    storage.close()
    assert load_catalog("no-such-dir") == []


# ---------------------------------------------------------------------------
# MCP tools with profile parameter
# ---------------------------------------------------------------------------


def test_mcp_olx_tools_profile_scoping(tmp_path, monkeypatch):
    from aios_core.mcp.gateway import GatewayConfig, MCPGateway
    from aios_core.modules.olx import AdCard, OLXStorage
    from aios_core.storage import Database

    registry_path = tmp_path / "profiles.sqlite"
    work_db = tmp_path / "work.sqlite"
    with ProfileStore(registry_path) as store:
        store.add(Profile(platform="olx", name="work", db_path=str(work_db)))
    with OLXStorage(work_db) as seeded:
        seeded.save_ads([AdCard(title="Только в work", url="http://x/p.html")])

    monkeypatch.setenv("AIOS_PROFILES_DB", str(registry_path))
    ProfileStore.reset_default()
    try:
        gateway = MCPGateway(
            config=GatewayConfig(
                constitution_dir=os.path.join(_PROJECT_ROOT, "docs/constitution"),
                policies_dir=os.path.join(_PROJECT_ROOT, "policies"),
                db_path=":memory:",
            ),
            db=Database(db_path=":memory:"),
        )
        # tools/list рекламирует параметр profile.
        listed = json.loads(
            gateway.handle_request(
                json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
            )
        )
        stats_tool = next(t for t in listed["result"]["tools"] if t["name"] == "olx_market_stats")
        assert "profile" in stats_tool["inputSchema"]["properties"]

        # С profile=work видна запись из БД профиля.
        response = json.loads(
            gateway.handle_request(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "tools/call",
                        "params": {"name": "olx_market_stats", "arguments": {"profile": "work"}},
                    }
                )
            )
        )
        assert "error" not in response, response.get("error")
        payload = json.loads(response["result"]["content"][0]["text"])
        assert payload["total_ads"] == 1

        # Без profile — общее хранилище (пустое).
        response = json.loads(
            gateway.handle_request(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {"name": "olx_market_stats", "arguments": {}},
                    }
                )
            )
        )
        payload = json.loads(response["result"]["content"][0]["text"])
        assert payload["total_ads"] == 0
    finally:
        ProfileStore.reset_default()


@pytest.mark.asyncio
async def test_rest_device_pool_flow(api_client):
    client, tmp_path = api_client

    empty = await client.get("/api/v1/devices")
    assert empty.json()["devices"] == []

    bad = await client.post("/api/v1/devices/lease", json={"profile": "olx:work"})
    assert bad.status_code == 409  # пул пуст

    reg = await client.post(
        "/api/v1/devices/register",
        json={
            "serial": "emulator-5556",
            "avd_name": "aios-olx-1",
        },
    )
    assert reg.status_code == 201
    await client.post("/api/v1/devices/register", json={"serial": "emulator-5558"})

    no_serial = await client.post("/api/v1/devices/register", json={})
    assert no_serial.status_code == 400

    lease = await client.post("/api/v1/devices/lease", json={"profile": "olx:work"})
    assert lease.status_code == 200
    leased_serial = lease.json()["serial"]
    assert lease.json()["profile_key"] == "olx:work"

    # Реестр профилей синхронизирован после создания профиля и повторной аренды.
    await client.post(
        "/api/v1/profiles",
        json={
            "platform": "olx",
            "name": "work",
            "db_path": str(tmp_path / "w.sqlite"),
        },
    )
    lease2 = await client.post("/api/v1/devices/lease", json={"profile": "olx:work"})
    assert lease2.json()["serial"] == leased_serial
    shown = await client.get("/api/v1/profiles/olx/work")
    assert shown.json()["device_serial"] == leased_serial

    second = await client.post("/api/v1/devices/lease", json={"profile": "olx:home"})
    assert second.status_code == 200
    full = await client.post("/api/v1/devices/lease", json={"profile": "olx:z"})
    assert full.status_code == 409

    pin = await client.post(
        "/api/v1/devices/lease",
        json={
            "profile": "olx:z",
            "serial": leased_serial,
        },
    )
    assert pin.status_code == 409  # устройство занято

    unknown = await client.post(
        "/api/v1/devices/lease",
        json={
            "profile": "olx:z",
            "serial": "ghost",
        },
    )
    assert unknown.status_code == 400

    hb = await client.post("/api/v1/devices/heartbeat", json={"serial": leased_serial})
    assert hb.json()["ok"] is True

    release = await client.post("/api/v1/devices/release", json={"profile": "olx:work"})
    assert release.json()["released"] == leased_serial

    listed = await client.get("/api/v1/devices")
    assert len(listed.json()["devices"]) == 2

    reap = await client.post("/api/v1/devices/reap", json={"max_silence_s": 86400})
    assert reap.json()["reaped"] == []
