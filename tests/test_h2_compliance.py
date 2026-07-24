"""Tests for alpha.22: compliance guard enforcement, storage audit-log,
telemetry counters (receipts/outbox) and Prometheus alert rules.
"""

import json
from pathlib import Path

import pytest
import yaml

from aios_core.platforms import (
    compliance_block,
    compliance_guard,
    get_platform,
    load_catalog_file,
    rate_limit_hours,
)
from aios_core.platforms import descriptor as descriptor_mod


def _write_yaml(tmp_path, platform, package, compliance=None):
    (tmp_path / f"{platform}.yaml").write_text(
        yaml.safe_dump(
            {
                "name": platform,
                "android_package": package,
                "agent_module": f"aios_core.modules.{platform}",
                "storage_class": f"aios_core.modules.{platform}.storage.TestStorage",
                "extras": {"compliance": compliance or {}, "parser_hints": {}},
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# compliance_guard
# ---------------------------------------------------------------------------


def test_guard_no_policy_denies_guarded_actions(tmp_path):
    _write_yaml(tmp_path, "mystery", "com.mystery")
    for action in ("autopost", "collect", "auto_send"):
        check = compliance_guard("mystery", action, directory=str(tmp_path))
        assert check["allowed"] is False, action
        assert check["reason"]  # честное объяснение всегда прилагается
    # черновик в очередь — не guarded-внешнее действие, разрешён
    assert compliance_guard("mystery", "send", directory=str(tmp_path))["allowed"] is True


def test_guard_yaml_missing_descriptor(tmp_path):
    check = compliance_guard("ghost", "collect", directory=str(tmp_path))
    assert check["allowed"] is False
    assert check["policy"] == {}


def test_guard_policy_matrix(tmp_path):
    _write_yaml(
        tmp_path,
        "strict",
        "com.strict",
        compliance={
            "autopost_allowed": False,
            "messenger": "approval-only",
            "collector": False,
            "note": "ToS: no automation",
        },
    )
    _write_yaml(
        tmp_path,
        "open",
        "com.open",
        compliance={
            "autopost_allowed": True,
            "messenger": "open",
            "collector": True,
            "actions_per_hour": 60,
        },
    )
    directory = str(tmp_path)
    for action in ("autopost", "collect", "auto_send"):
        assert compliance_guard("strict", action, directory=directory)["allowed"] is False
        assert compliance_guard("open", action, directory=directory)["allowed"] is True
    assert compliance_guard("strict", "send", directory=directory)["allowed"] is True
    assert "approval" in compliance_guard("strict", "auto_send", directory=directory)["reason"]
    assert compliance_guard("open", "send", directory=directory)["allowed"] is True
    assert rate_limit_hours("open", directory=directory) == 60
    assert rate_limit_hours("strict", directory=directory) is None
    assert compliance_block("open", directory=directory)["messenger"] == "open"


def test_guard_messenger_none_disables_even_drafts(tmp_path):
    _write_yaml(tmp_path, "dead", "com.dead", compliance={"messenger": "none"})
    check = compliance_guard("dead", "send", directory=str(tmp_path))
    assert check["allowed"] is False


def test_guard_unknown_action_is_honest_error(tmp_path):
    with pytest.raises(ValueError):
        compliance_guard("olx", "teleport", directory=str(tmp_path))


def test_scaffold_generates_deny_by_default_compliance(tmp_path):
    from aios_core.platforms import scaffold_platform

    scaffold_platform(
        "scafpol",
        "com.scaf.pol",
        project_root=str(tmp_path),
        description="privacy test platform",
    )
    written = yaml.safe_load((tmp_path / "platforms" / "scafpol.yaml").read_text(encoding="utf-8"))
    policy = written["extras"]["compliance"]
    assert policy["autopost_allowed"] is False
    assert policy["messenger"] == "approval-only"
    assert policy["collector"] is False
    descriptor_mod._PLATFORMS.pop("scafpol", None)


def test_catalog_platforms_carry_compliance_blocks():
    loaded = []
    for name in ("olx", "instagram", "whatsapp", "viber", "tiktok", "facebook"):
        loaded.extend(load_catalog_file(f"platforms/{name}.yaml"))
    try:
        for name in ("olx", "instagram", "whatsapp", "viber", "tiktok", "facebook"):
            descriptor = get_platform(name)
            policy = descriptor.extras["compliance"]
            assert policy["messenger"] == "approval-only", name
        assert get_platform("olx").extras["compliance"]["autopost_allowed"] is True
        assert get_platform("whatsapp").extras["compliance"]["autopost_allowed"] is False
    finally:
        for descriptor in loaded:
            descriptor_mod._PLATFORMS.pop(descriptor.name, None)


# ---------------------------------------------------------------------------
# enforcement at guarded boundaries (CLI + composer)
# ---------------------------------------------------------------------------


def test_cli_dm_send_auto_send_denied_by_compliance(tmp_path, capsys):
    from aios_cli import main
    from aios_core.platforms import ProfileStore

    loaded = load_catalog_file("platforms/whatsapp.yaml")
    (tmp_path / "platforms").mkdir()
    (tmp_path / "platforms" / "whatsapp.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "whatsapp",
                "android_package": "com.whatsapp",
                "agent_module": "aios_core.modules.whatsapp",
                "storage_class": "aios_core.modules.whatsapp.storage.WhatsAppStorage",
                "extras": {
                    "compliance": {
                        "autopost_allowed": False,
                        "messenger": "approval-only",
                        "collector": False,
                    },
                    "parser_hints": {},
                },
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    import os

    os.chdir(tmp_path)  # messenger hints/yaml читаются из cwd
    try:
        main(
            [
                "whatsapp",
                "dm-send",
                "--chat",
                "c:1",
                "--text",
                "hi",
                "--db",
                str(tmp_path / "wa.sqlite"),
                "--auto-send",
            ]
        )
        out = json.loads(capsys.readouterr().out)
        assert "error" in out
        assert out["compliance"]["allowed"] is False
        # обычный guarded draft — разрешён
        main(
            [
                "whatsapp",
                "dm-send",
                "--chat",
                "c:1",
                "--text",
                "hi",
                "--db",
                str(tmp_path / "wa.sqlite"),
            ]
        )
        draft = json.loads(capsys.readouterr().out)
        assert draft["status"] == "queued"
    finally:
        os.chdir(Path(__file__).resolve().parent.parent)
        ProfileStore.reset_default()
        for d in loaded:
            descriptor_mod._PLATFORMS.pop(d.name, None)


def test_cli_platforms_reels_denied_without_collector(tmp_path, capsys, monkeypatch):
    from aios_cli import main
    from aios_core.platforms import ProfileStore

    _write_yaml(
        tmp_path,
        "tiktuk",
        "com.tiktuk",
        compliance={"autopost_allowed": False, "messenger": "approval-only", "collector": False},
    )
    monkeypatch.setenv("AIOS_PROFILES_DB", str(tmp_path / "profiles.sqlite"))
    ProfileStore.reset_default()
    main(
        [
            "platforms",
            "reels",
            "--platform",
            "tiktuk",
            "--directory",
            str(tmp_path),
            "--serial",
            "fake-s",
        ]
    )
    out = json.loads(capsys.readouterr().out)
    assert "error" in out
    assert out["compliance"]["action"] == "collect"
    assert out["compliance"]["allowed"] is False


def test_instagram_post_composer_compliance_denies(tmp_path):
    from aios_core.modules.instagram.own_posts import PostComposer

    _write_yaml(
        tmp_path,
        "instagram",
        "com.instagram.android",
        compliance={
            "autopost_allowed": False,
            "messenger": "approval-only",
            "collector": True,
            "note": "test policy",
        },
    )

    class _ADB:
        package = "com.instagram.android"

        @property
        def adb(self):
            return "adb"

        def run(self, command):
            return {"code": 1, "stdout": "", "stderr": "must not run"}

        def tap(self, x, y):
            raise AssertionError("device must be untouched")

    image = tmp_path / "pic.jpg"
    image.write_bytes(b"\xff\xd8\xff")
    composer = PostComposer(adb=_ADB())
    result = composer.publish(str(image), "hello", confirm=True, directory=str(tmp_path))
    assert result["status"] == "denied"
    assert result["compliance"]["action"] == "autopost"
    # а dry-run и на запрещающей политике — только план:
    plan = composer.publish(str(image), "hello", confirm=False, directory=str(tmp_path))
    assert plan["status"] == "dry-run"


def test_repo_instagram_policy_allows_confirmed_post():
    from aios_core.platforms.compliance import compliance_guard

    check = compliance_guard("instagram", "autopost", directory="platforms")
    assert check["allowed"] is True  # только с явным --confirm (note в yaml)


# ---------------------------------------------------------------------------
# audit log in storage
# ---------------------------------------------------------------------------


def test_storage_audit_tracks_outbox_lifecycle():
    from aios_core.modules.whatsapp import WhatsAppStorage

    storage = WhatsAppStorage(":memory:")
    outbox_id = storage.enqueue_outbox("chat:a", "Привет", interlocutor="anna")
    storage.outbox_mark(outbox_id, "sent", result="ok")
    entries = storage.audit_list()
    actions = [row["action"] for row in entries]
    assert "outbox.enqueue" in actions
    assert "outbox.mark" in actions
    mark = storage.audit_list(action="outbox.mark")[0]
    assert mark["ref"] == str(outbox_id)
    assert "status=sent" in mark["detail"]
    # ограничение лимита
    for i in range(5):
        storage.audit("test.tick", detail=str(i))
    assert len(storage.audit_list(limit=3)) == 3
    storage.close()


# ---------------------------------------------------------------------------
# telemetry counters (receipts/outbox) + alert rules
# ---------------------------------------------------------------------------


def test_telemetry_platform_db_counters(tmp_path, monkeypatch):
    from aios_core.modules.whatsapp import WhatsAppStorage
    from aios_core.platforms.telemetry import fleet_snapshot, prometheus_metrics

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    storage = WhatsAppStorage(str(data_dir / "whatsapp.sqlite"))
    storage.check_and_record("fp1", kind="video")
    storage.check_and_record("fp2", kind="video", ref="q")
    storage.check_and_record("fp3", kind="ad")
    storage.enqueue_outbox("chat:a", "t1")
    storage.enqueue_outbox("chat:b", "t2")
    storage.close()
    # чужая битая база не ломает метрики:
    (data_dir / "broken.sqlite").write_bytes(b"not-a-sqlite")

    for env in ("AIOS_SHARDS_DB", "AIOS_PROFILES_DB", "AIOS_DEVICES_DB"):
        monkeypatch.setenv(env, str(tmp_path / f"{env}.sqlite"))
    text = prometheus_metrics(data_dir=str(data_dir), catalog_dir=str(tmp_path))
    assert 'aios_seen_receipts{platform="whatsapp",kind="video"} 2' in text
    assert 'aios_seen_receipts{platform="whatsapp",kind="ad"} 1' in text
    assert 'aios_outbox_pending{platform="whatsapp"} 2' in text
    assert "broken" not in text

    snapshot = fleet_snapshot(data_dir=str(data_dir), catalog_dir=str(tmp_path))
    assert snapshot["platform_db"]["whatsapp"]["seen_video"] == 2


def test_alert_rules_yaml_valid_and_cover_critical_paths():
    alerts = yaml.safe_load(Path("deploy/monitoring/aios-alerts.yml").read_text(encoding="utf-8"))
    names = [rule["alert"] for group in alerts["groups"] for rule in group["rules"]]
    for expected in (
        "AIOSDown",
        "AIOSShardWorkersDown",
        "AIOSQueueBacklog",
        "AIOSStaleClaims",
        "AIOSFleetExhausted",
        "AIOSOutboxApprovalLag",
    ):
        assert expected in names
    # все правила несут severity
    for group in alerts["groups"]:
        for rule in group["rules"]:
            assert rule["labels"]["severity"] in ("warning", "critical")
    prometheus_cfg = yaml.safe_load(
        Path("deploy/monitoring/prometheus.yml").read_text(encoding="utf-8")
    )
    assert "aios-alerts.yml" in prometheus_cfg["rule_files"]
