"""Tests for the lease waitlist, shard router, APK auto-scaffold and
their CLI/REST surfaces."""

import json
import os

import pytest
from httpx import ASGITransport, AsyncClient

from aios_core.platforms import DevicePool, ShardRouter
from aios_core.platforms.scaffold import inspect_apk, scaffold_from_apk

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# Waitlist
# ---------------------------------------------------------------------------


def test_waitlist_priority_fifo_idempotent_and_cancel():
    with DevicePool(":memory:") as pool:
        id_b = pool.enqueue("olx:b", priority=1)
        assert pool.enqueue("olx:b", priority=9) == id_b  # идемпотентно
        id_c = pool.enqueue("olx:c", priority=5)
        id_a = pool.enqueue("olx:a")
        queue = pool.waitlist()
        # priority DESC, затем FIFO
        assert [w["profile_key"] for w in queue] == ["olx:c", "olx:b", "olx:a"]
        assert pool.cancel_wait("olx:b") is True
        assert pool.cancel_wait("olx:b") is False
        assert [w["profile_key"] for w in pool.waitlist()] == ["olx:c", "olx:a"]
        assert id_c != id_a


def test_waitlist_served_on_release_and_reap():
    with DevicePool(":memory:") as pool:
        pool.register("e1")
        pool.register("e2")
        pool.lease("olx:a")
        pool.lease("olx:b")
        pool.enqueue("olx:c", priority=5)
        pool.enqueue("olx:d", priority=1)
        pool.release("olx:a")
        # release обслужил очередь: olx:c (выше приоритет) получил e1.
        assert pool.device_for("olx:c")["serial"] == "e1"
        served = [w for w in pool.waitlist("served")]
        assert [w["profile_key"] for w in served] == ["olx:c"]

        # reap_stale: мёртвое устройство → offline, его аренда освобождается,
        # но очередь ждёт — свободных устройств не осталось.
        with pool._lock, pool._conn:
            pool._conn.execute(
                "UPDATE devices SET last_heartbeat = '2020-01-01T00:00:00+00:00' "
                "WHERE serial = 'e2'"
            )
        reaped = pool.reap_stale()
        assert reaped == ["e2"]
        assert pool.device_for("olx:b") is None  # аренда мёртвого снята
        assert pool.device_for("olx:d") is None  # ждать дальше
        assert [w["profile_key"] for w in pool.waitlist()] == ["olx:d"]
        # …пока живое устройство не освободится.
        pool.release("olx:c")
        assert pool.device_for("olx:d")["serial"] == "e1"


def test_waitlist_respects_platform_quota():
    with DevicePool(":memory:") as pool:
        pool.set_limit("max_busy:olx", 1)
        pool.register("e1")
        pool.lease("olx:a")
        pool.enqueue("olx:b")
        assert pool.serve_waitlist() == []  # квота держит очередь


# ---------------------------------------------------------------------------
# ShardRouter
# ---------------------------------------------------------------------------


def test_shards_hosts_crud_and_sticky_route():
    with ShardRouter(":memory:") as router:
        assert router.hosts() == []
        router.add_host("h1", "http://h1.local:8000")
        router.add_host("h2", "http://h2.local:8000")
        assert len(router.hosts()) == 2

        first = router.route_for("olx:work")
        assert first["host"] in ("h1", "h2")
        assert first["url"].endswith("/profiles/olx/work")
        # Липкость: повторный роутинг — тот же хост (даже после новых хостов).
        router.add_host("h3", "http://h3.local:8000")
        assert router.route_for("olx:work")["host"] == first["host"]

        # Отказ хоста → автоматический переназначение на здоровый.
        router.set_healthy(first["host"], False)
        moved = router.route_for("olx:work")
        assert moved["host"] != first["host"]

        # unroute + reproduce rendezvous determinism.
        router.unroute("olx:work")
        assert router.route_for("olx:work")["host"] == moved["host"]

        router.remove_host(moved["host"])
        assert router.reassign("ghost") == 0


def test_shards_no_healthy_hosts():
    with ShardRouter(":memory:") as router:
        router.add_host("h1", "http://h1:8000")
        router.set_healthy("h1", False)
        assert router.route_for("olx:x") is None


# ---------------------------------------------------------------------------
# APK auto-scaffold
# ---------------------------------------------------------------------------

_BADGING = """
package: name='ua.slando' versionCode='2410' versionName='14.49.0'
application-label:'OLX'
launchable-activity: name='ua.slando.activity.MainActivity'
targetSdkVersion:'34'
"""


def _fake_runner(path):
    return {"code": 0, "stdout": _BADGING, "stderr": ""}


def test_inspect_apk_parses_badging():
    spec = inspect_apk("olx.apk", runner=_fake_runner)
    assert spec["android_package"] == "ua.slando"
    assert spec["candidate_name"] == "slando"
    assert spec["app_label"] == "OLX"
    assert spec["target_sdk"] == "34"


def test_inspect_apk_errors():
    with pytest.raises(ValueError):
        inspect_apk("not-an-apk.zip", runner=_fake_runner)
    with pytest.raises(ValueError) as exc:
        inspect_apk("bad.apk", runner=lambda p: {"code": 1, "stdout": "", "stderr": "no aapt"})
    assert "aapt" in str(exc.value)
    with pytest.raises(ValueError):
        inspect_apk("empty.apk", runner=lambda p: {"code": 0, "stdout": "junk", "stderr": ""})


def test_scaffold_from_apk_dry_run_and_real(tmp_path):
    result = scaffold_from_apk(
        "olx.apk",
        name="olx-dupe",
        project_root=tmp_path,
        dry_run=True,
        runner=_fake_runner,
    )
    assert result["spec"]["android_package"] == "ua.slando"
    assert any(p.endswith("olx-dupe.yaml") for p in result["files"])
    assert not (tmp_path / "platforms").exists()

    result = scaffold_from_apk("olx.apk", project_root=tmp_path, runner=_fake_runner)
    yaml_text = (tmp_path / "platforms/slando.yaml").read_text()
    assert "ua.slando" in yaml_text
    assert "auto-scaffold from olx.apk" in yaml_text
    assert (tmp_path / "aios_core/modules/slando/storage.py").exists()


# ---------------------------------------------------------------------------
# CLI surfaces
# ---------------------------------------------------------------------------


def test_cli_devices_waitlist_flow(tmp_path, monkeypatch, capsys):
    from aios_cli import main

    monkeypatch.setenv("AIOS_DEVICES_DB", str(tmp_path / "devices.sqlite"))
    main(["devices", "register", "--serial", "e1"])
    json.loads(capsys.readouterr().out)
    main(["devices", "lease", "--profile", "olx:a"])
    json.loads(capsys.readouterr().out)

    # Пул исчерпан: lease --enqueue ставит в очередь.
    main(["devices", "lease", "--profile", "olx:b", "--enqueue", "--priority", "5"])
    out = json.loads(capsys.readouterr().out)
    assert out["queued"] >= 1 and out["profile"] == "olx:b"

    main(["devices", "waitlist"])
    queue = json.loads(capsys.readouterr().out)
    assert [w["profile_key"] for w in queue] == ["olx:b"]

    # release обслуживает очередь автоматически.
    main(["devices", "release", "--profile", "olx:a"])
    json.loads(capsys.readouterr().out)
    main(["devices", "waitlist"])
    assert json.loads(capsys.readouterr().out) == []

    main(["devices", "enqueue", "--profile", "olx:c"])
    json.loads(capsys.readouterr().out)
    main(["devices", "cancel-wait", "--profile", "olx:c"])
    assert json.loads(capsys.readouterr().out)["cancelled"] is True


def test_cli_shards_flow(tmp_path, monkeypatch, capsys):
    from aios_cli import main

    monkeypatch.setenv("AIOS_SHARDS_DB", str(tmp_path / "shards.sqlite"))
    main(["shards", "add", "--host", "h1", "--base-url", "http://h1:8000"])
    json.loads(capsys.readouterr().out)
    main(["shards", "list"])
    assert len(json.loads(capsys.readouterr().out)) == 1

    main(["shards", "route", "--profile", "olx:work"])
    route = json.loads(capsys.readouterr().out)
    assert route["host"] == "h1"
    main(["shards", "route", "--profile", "olx:work"])
    assert json.loads(capsys.readouterr().out)["host"] == "h1"  # sticky

    main(["shards", "unroute", "--profile", "olx:work"])
    assert json.loads(capsys.readouterr().out)["unrouted"] is True

    main(["shards", "remove", "--host", "h1"])
    assert json.loads(capsys.readouterr().out)["removed"] is True
    main(["shards", "route", "--profile", "olx:work"])
    assert "error" in json.loads(capsys.readouterr().out)  # нет здоровых хостов


def test_cli_platforms_from_apk_dry_run(tmp_path, capsys, monkeypatch):
    import aios_core.platforms.scaffold as scaffold_mod
    from aios_cli import main

    # Подменяем _badging на тестовый runner (в CI нет aapt).
    monkeypatch.setattr(scaffold_mod, "_badging", _fake_runner)
    main(["platforms", "from-apk", "olx.apk", "--dry-run", "--root", str(tmp_path)])
    out = json.loads(capsys.readouterr().out)
    assert out["spec"]["android_package"] == "ua.slando"
    assert any(p.endswith("slando.yaml") for p in out["planned"])
    assert not (tmp_path / "platforms").exists()


# ---------------------------------------------------------------------------
# REST surfaces
# ---------------------------------------------------------------------------


@pytest.fixture
async def client():
    from aios_core.api.app import AIOSAPI
    from aios_core.platforms import ProfileStore

    store = ProfileStore(":memory:")
    api = AIOSAPI(
        db_path=":memory:",
        constitution_dir=os.path.join(_PROJECT_ROOT, "docs/constitution"),
        policies_dir=os.path.join(_PROJECT_ROOT, "policies"),
        auth_required=False,
        profile_store=store,
        device_pool=DevicePool(":memory:"),
        shard_router=ShardRouter(":memory:"),
    )
    app = api.create_starlette_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    store.close()


async def test_rest_waitlist_flow(client):
    await client.post("/api/v1/devices/register", json={"serial": "e1"})
    await client.post("/api/v1/devices/lease", json={"profile": "olx:a"})

    busy = await client.post("/api/v1/devices/lease", json={"profile": "olx:b"})
    assert busy.status_code == 409

    queued = await client.post(
        "/api/v1/devices/lease",
        json={
            "profile": "olx:b",
            "enqueue": True,
            "priority": 3,
        },
    )
    assert queued.status_code == 202
    assert queued.json()["queued"] >= 1

    listing = await client.get("/api/v1/devices/waitlist")
    assert [w["profile_key"] for w in listing.json()["waitlist"]] == ["olx:b"]

    # release обслуживает очередь.
    await client.post("/api/v1/devices/release", json={"profile": "olx:a"})
    listing = await client.get("/api/v1/devices/waitlist")
    assert listing.json()["waitlist"] == []
    served = await client.get("/api/v1/devices/waitlist?status=served")
    assert served.json()["waitlist"][0]["served_serial"] == "e1"

    await client.post(
        "/api/v1/devices/lease",
        json={
            "profile": "olx:z",
            "enqueue": True,
        },
    )
    cancelled = await client.post("/api/v1/devices/waitlist/cancel", json={"profile": "olx:z"})
    assert cancelled.json()["cancelled"] is True


async def test_rest_shards_flow(client):
    added = await client.post(
        "/api/v1/shards",
        json={
            "host": "h1",
            "base_url": "http://h1:8000",
        },
    )
    assert added.status_code == 201

    bad = await client.post("/api/v1/shards", json={"host": "h2"})
    assert bad.status_code == 400

    route = await client.post("/api/v1/shards/route", json={"profile": "olx:work"})
    assert route.json()["host"] == "h1"
    again = await client.post("/api/v1/shards/route", json={"profile": "olx:work"})
    assert again.json()["host"] == "h1"  # липкость через REST

    no_profile = await client.post("/api/v1/shards/route", json={})
    assert no_profile.status_code == 400

    missing = await client.delete("/api/v1/shards/ghost")
    assert missing.status_code == 404

    deleted = await client.delete("/api/v1/shards/h1")
    assert deleted.json()["removed"] is True
    empty = await client.post("/api/v1/shards/route", json={"profile": "olx:x"})
    assert empty.status_code == 409

    unrouted = await client.request(
        "DELETE",
        "/api/v1/shards/route",
        json={"profile": "olx:work"},
    )
    assert unrouted.status_code == 200
