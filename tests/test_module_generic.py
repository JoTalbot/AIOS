"""Tests for descriptor-driven generic module REST surfaces, pool quotas
and the cron-plan generator."""

import json
import os

import pytest
from httpx import ASGITransport, AsyncClient

from aios_core.platforms import DevicePool, PlatformDescriptor, Profile, ProfileStore
from aios_core.platforms import descriptor as descriptor_mod
from aios_core.platforms import register_platform

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def demo_platform(tmp_path):
    """Демонстрационная платформа с фабриками OLX-совместимого модуля."""

    def storage_factory(db_path):
        from aios_core.modules.olx import OLXStorage

        return OLXStorage(db_path)

    register_platform(
        PlatformDescriptor(
            name="demo",
            android_package="ua.demo.app",
            agent_module="demo.agent",
            storage_factory=storage_factory,
            legacy_default_db=str(tmp_path / "demo-default.sqlite"),
        )
    )
    yield
    descriptor_mod._PLATFORMS.pop("demo", None)


@pytest.fixture
async def client(demo_platform, tmp_path):
    from aios_core.api.app import AIOSAPI

    store = ProfileStore(":memory:")
    store.add(
        Profile(
            platform="demo",
            name="main",
            db_path=str(tmp_path / "demo-main.sqlite"),
            is_default=True,
        )
    )
    api = AIOSAPI(
        db_path=":memory:",
        constitution_dir=os.path.join(_PROJECT_ROOT, "docs/constitution"),
        policies_dir=os.path.join(_PROJECT_ROOT, "policies"),
        auth_required=False,
        profile_store=store,
        device_pool=DevicePool(":memory:"),
    )
    app = api.create_starlette_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    store.close()


ADS = [
    {
        "title": "Демо товар А",
        "price": 100.0,
        "currency": "UAH",
        "city": "Київ",
        "url": "http://demo/a.html",
        "query": "q",
    },
    {
        "title": "Демо товар Б",
        "price": 250.0,
        "currency": "UAH",
        "city": "Львів",
        "url": "http://demo/b.html",
        "query": "q",
    },
]


async def test_generic_module_data_plane(client):
    # Пустой data-plane новой платформы работает без кода.
    empty = await client.get("/api/v1/modules/demo/ads")
    assert empty.status_code == 200
    assert empty.json()["total"] == 0

    # Ingest от внешнего коллектора (платформа-агностичный формат AdCard).
    ingest = await client.post("/api/v1/modules/demo/ads/ingest", json={"ads": ADS, "query": "q"})
    assert ingest.status_code == 200
    assert ingest.json()["new_ads"] == 2
    # Повторный ingest идемпотентен.
    again = await client.post("/api/v1/modules/demo/ads/ingest", json={"ads": ADS, "query": "q"})
    assert again.json()["new_ads"] == 0

    listed = await client.get("/api/v1/modules/demo/ads", params={"query": "q"})
    assert listed.json()["count"] == 2
    assert listed.json()["platform"] == "demo"
    fp = listed.json()["items"][0]["fingerprint"]

    stats = await client.get("/api/v1/modules/demo/stats", params={"query": "q"})
    assert stats.status_code == 200
    body = stats.json()
    assert body["total_ads"] == 2
    assert body["min_price"] == 100.0 and body["max_price"] == 250.0
    assert body["platform"] == "demo"

    history = await client.get(f"/api/v1/modules/demo/ads/{fp}/history")
    assert history.status_code == 200
    assert len(history.json()["history"]) >= 1

    snapshot = await client.post(
        "/api/v1/modules/demo/own/snapshot",
        json={"ads": [{"title": "Моё демо", "price": 150.0, "ad_id": "own1"}]},
    )
    assert snapshot.status_code == 200
    own = await client.get("/api/v1/modules/demo/own")
    assert own.json()["count"] == 1
    assert own.json()["items"][0]["ad_id"] == "own1"

    unknown = await client.get("/api/v1/modules/ghost/ads")
    assert unknown.status_code == 404


async def test_generic_module_profile_isolation(client, tmp_path):
    # Ingest в профиль main: данные видны по ?profile=main.
    await client.post("/api/v1/modules/demo/ads/ingest?profile=main", json={"ads": ADS})
    scoped = await client.get("/api/v1/modules/demo/ads?profile=main")
    assert scoped.json()["total"] == 2

    # main — дефолт реестра, поэтому безпрофильный запрос идёт туда же
    # (проектный приоритет резолвера: registry default > legacy path).
    default_view = await client.get("/api/v1/modules/demo/ads")
    assert default_view.json()["total"] == 2

    # Второй профиль — собственное пустое хранилище (изоляция).
    from aios_core.platforms import Profile as _Profile

    # регистрируем через REST, чтобы проверить и его:
    created = await client.post(
        "/api/v1/profiles",
        json={
            "platform": "demo",
            "name": "second",
            "db_path": str(tmp_path / "demo-second.sqlite"),
        },
    )
    assert created.status_code == 201
    second = await client.get("/api/v1/modules/demo/ads?profile=second")
    assert second.json()["total"] == 0

    # olx-роуты не затронуты: статические матчатся раньше generic.
    olx_ads = await client.get("/api/v1/modules/olx/ads")
    assert olx_ads.status_code == 200
    assert "platform" not in olx_ads.json()


# ---------------------------------------------------------------------------
# Pool quotas
# ---------------------------------------------------------------------------


def test_pool_quota_caps():
    with DevicePool(":memory:") as pool:
        pool.set_limit("max_devices", 2)
        pool.register("a")
        pool.register("b")
        with pytest.raises(ValueError):
            pool.register("c")
        pool.register("a")  # повторная регистрация не считается

        pool.set_limit("max_busy:olx", 1)
        assert pool.lease("olx:x") is not None
        assert pool.lease("olx:y") is None  # квота платформы
        assert pool.lease("other:y") is not None  # другая платформа не ограничена
        assert pool.lease("olx:x")["serial"] == "a"  # продление — не новая аренда
        assert pool.lease("olx:y", serial="b") is None  # pinned тоже под квотой

        assert pool.limits() == {"max_busy:olx": 1, "max_devices": 2}


def test_ensure_device_respects_max_avds_quota():
    from aios_core.platforms import ensure_device

    calls = []
    with DevicePool(":memory:") as pool:
        pool.set_limit("max_avds", 0)
        record = ensure_device(
            "olx:x",
            pool=pool,
            create_avd=lambda n: calls.append(n) or True,
            start_emulator=lambda n: None,
            wait_serial=lambda k: "emulator-1",
            list_devices=lambda: [],
        )
        assert record is None
        assert calls == []  # до создания AVD дело не дошло


async def test_rest_devices_limits(client):
    await client.post("/api/v1/devices/limits", json={"key": "max_devices", "value": 1})
    limits = await client.get("/api/v1/devices/limits")
    assert limits.json()["limits"]["max_devices"] == 1

    await client.post("/api/v1/devices/register", json={"serial": "e-1"})
    capped = await client.post("/api/v1/devices/register", json={"serial": "e-2"})
    assert capped.status_code == 400
    assert "max_devices" in capped.json()["error"]

    bad = await client.post("/api/v1/devices/limits", json={"key": "x"})
    assert bad.status_code == 400


# ---------------------------------------------------------------------------
# cron-plan
# ---------------------------------------------------------------------------


def test_cli_cron_plan_per_profile(tmp_path, monkeypatch, capsys):
    from aios_cli import main

    registry = tmp_path / "profiles.sqlite"
    monkeypatch.setenv("AIOS_PROFILES_DB", str(registry))
    ProfileStore.reset_default()
    try:
        main(["profiles", "add", "--platform", "olx", "--name", "work"])
        json.loads(capsys.readouterr().out)
        main(["profiles", "add", "--platform", "olx", "--name", "home"])
        json.loads(capsys.readouterr().out)

        capsys.readouterr()  # сброс
        main(
            [
                "cron-plan",
                "--platform",
                "olx",
                "--interval",
                "10",
                "--webhook",
                "https://hook.example/x",
            ]
        )
        plan = capsys.readouterr().out
        assert "autowatch --profile work" in plan
        assert "autowatch --profile home" in plan
        assert "--webhook https://hook.example/x" in plan
        assert "devices monitor --once" in plan
        assert "*/10 * * * *" in plan
        assert f"AIOS_PROFILES_DB={registry}" in plan

        target = tmp_path / "aios.cron"
        main(["cron-plan", "--platform", "olx", "--write", str(target)])
        out = json.loads(capsys.readouterr().out)
        assert out["written"] == str(target)
        assert "autowatch --profile work" in target.read_text()
    finally:
        ProfileStore.reset_default()


def test_cli_devices_limits(tmp_path, monkeypatch, capsys):
    from aios_cli import main

    monkeypatch.setenv("AIOS_DEVICES_DB", str(tmp_path / "devices.sqlite"))
    main(["devices", "limits", "--set", "max_busy:olx=3"])
    out = json.loads(capsys.readouterr().out)
    assert out == {"max_busy:olx": 3}
    main(["devices", "limits"])
    assert json.loads(capsys.readouterr().out)["max_busy:olx"] == 3
