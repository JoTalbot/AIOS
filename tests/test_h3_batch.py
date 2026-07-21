"""Tests for alpha.23 batch: AI-советник Direct-черновиков (draft-only),
marker drift events → telemetry, K8s operator manifests + controller.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from aios_core.platforms import (
    advise_drafts,
    check_platform_markers,
    drift_events_summary,
    load_catalog_file,
    reply_draft,
)
from aios_core.platforms import descriptor as descriptor_mod


@dataclass
class _Thread:
    interlocutor: str
    snippet: str
    ad_title: str = None
    unread_count: int = 0

    @property
    def key(self):
        return f"chat-{self.interlocutor}"


# ---------------------------------------------------------------------------
# reply_draft templates
# ---------------------------------------------------------------------------

def test_reply_draft_classifies_availability_uk():
    text = reply_draft("anna", "Добрий день, це ще актуально?",
                       ad_title="Дрель Bosch")
    assert text.startswith("Добрий день, anna!")
    assert "ще актуально" in text
    assert "«Дрель Bosch»" in text


def test_reply_draft_classifies_price_en():
    text = reply_draft("bob", "What is the price? still available?",
                       ad_title="Drill")
    assert text.startswith("Hello bob!")
    assert "price" in text.lower()
    assert '"Drill"' in text


def test_reply_draft_generic_and_fallbacks():
    text = reply_draft("", "як справи", ad_title=None)
    assert "друже" in text  # пустое имя → fallback
    assert "оголошення" in text  # пустой товар → fallback
    # латиница с en-триггерами переключает на en даже при uk локали
    assert reply_draft("kim", "hello, is this still available?")\
        .startswith("Hello kim!")


def test_advise_drafts_no_policy_denies_everything():
    from aios_core.modules.whatsapp import WhatsAppStorage

    storage = WhatsAppStorage(":memory:")
    report = advise_drafts(
        [_Thread("anna", "актуально?", unread_count=2)],
        storage, "ghost", directory="platforms")
    assert report["denied"] == 1
    assert report["enqueued"] == 0
    assert "deny-by-default" in report["denied_reason"]
    assert storage.outbox_list() == []  # ничего не попало даже в очередь
    audited = [row["action"] for row in storage.audit_list()]
    assert "advise.denied" in audited
    storage.close()


def test_advise_drafts_enqueues_only_unread_and_audits():
    from aios_core.modules.whatsapp import WhatsAppStorage

    storage = WhatsAppStorage(":memory:")
    threads = [
        _Thread("anna", "це ще актуально?", "Дрель", 1),
        _Thread("bob", "price? discount", "Дрель", 2),
        _Thread("cara", "уже отвечено", "X", 0),      # прочитано → skip
        _Thread("dave", "", "Y", 3),                  # пустой текст → skip
    ]
    report = advise_drafts(threads, storage, "whatsapp",
                           directory="platforms")
    assert report["engine"] == "template"
    assert report["enqueued"] == 2
    assert report["skipped"] == 2
    pending = storage.outbox_list(status="pending")
    assert len(pending) == 2
    texts = [row["text"] for row in pending]
    assert any("ще актуально" in t for t in texts)
    assert any("price" in t.lower() for t in texts)
    drafted = storage.audit_list(action="advise.draft")
    assert len(drafted) == 2
    assert pending[0]["status"] == "pending"  # только одобрение → flush
    storage.close()


def test_advise_drafts_pluggable_composer_engine():
    from aios_core.modules.whatsapp import WhatsAppStorage

    storage = WhatsAppStorage(":memory:")
    calls = []

    def composer(interlocutor, snippet, ad_title, locale):
        calls.append((interlocutor, snippet, ad_title, locale))
        return f"[LLM:{locale}] {interlocutor}! draft about {ad_title}"

    report = advise_drafts(
        [_Thread("anna", "актуально?", "Дрель", 1)],
        storage, "whatsapp", directory="platforms",
        composer=composer, locale="en")
    assert report["engine"] == "composer"
    assert report["enqueued"] == 1
    assert calls == [("anna", "актуально?", "Дрель", "en")]
    draft = report["entries"][0]["draft"]
    assert draft.startswith("[LLM:en]")
    audited = storage.audit_list(action="advise.draft")[0]
    assert "engine=composer" in audited["detail"]
    storage.close()


def test_cli_messenger_advise_offline_empty_is_honest(tmp_path, capsys,
                                                      monkeypatch):
    from aios_cli import main
    from aios_core.platforms import ProfileStore

    loaded = load_catalog_file("platforms/whatsapp.yaml")
    (tmp_path / "platforms").mkdir()
    (tmp_path / "platforms" / "whatsapp.yaml").write_text(yaml.safe_dump({
        "name": "whatsapp",
        "android_package": "com.whatsapp",
        "agent_module": "aios_core.modules.whatsapp",
        "storage_class": "aios_core.modules.whatsapp.storage.WhatsAppStorage",
        "extras": {"compliance": {"messenger": "approval-only"},
                   "parser_hints": {}},
    }, allow_unicode=True), encoding="utf-8")
    dump = tmp_path / "chats.xml"
    dump.write_text("<hierarchy><node text='' resource-id=''/></hierarchy>",
                    encoding="utf-8")
    monkeypatch.setenv("AIOS_PROFILES_DB", str(tmp_path / "p.sqlite"))
    ProfileStore.reset_default()
    import os
    previous = os.getcwd()
    os.chdir(tmp_path)
    try:
        main(["whatsapp", "advise", "--db", str(tmp_path / "wa.sqlite"),
              "--dump", str(dump)])
        out = json.loads(capsys.readouterr().out)
        assert out["platform"] == "whatsapp"
        assert out["enqueued"] == 0  # маркеры не откалиброваны — честно 0
        assert out["engine"] == "template"
    finally:
        os.chdir(previous)
        for d in loaded:
            descriptor_mod._PLATFORMS.pop(d.name, None)


# ---------------------------------------------------------------------------
# marker drift events
# ---------------------------------------------------------------------------

_BASELINE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node text="Пошук" resource-id="com.xplat:id/searchBar"/>
  <node text="" resource-id="com.xplat:id/adCard">
    <node text="Продам велосипед" resource-id=""/>
    <node text="4 500 грн" resource-id=""/>
    <node text="Київ" resource-id=""/>
  </node>
  <node text="" resource-id="com.xplat:id/adCard">
    <node text="iPhone 12 128GB" resource-id=""/>
    <node text="12 000 грн" resource-id=""/>
    <node text="Дніпро" resource-id=""/>
  </node>
</hierarchy>"""

_DRIFTED_XML = _BASELINE_XML.replace("adCard", "listingTile")

_HINTS = {"card_markers": [{"resource_id": "com.xplat:id/adCard"}]}


def _write_descriptor(tmp_path, platform, hints):
    (tmp_path / f"{platform}.yaml").write_text(yaml.safe_dump({
        "name": platform, "android_package": "pkg",
        "agent_module": "aios_core.modules.olx",
        "extras": {"parser_hints": hints},
    }), encoding="utf-8")


def test_drift_events_persisted_only_on_drift(tmp_path):
    _write_descriptor(tmp_path, "xplat", _HINTS)
    db = tmp_path / "drift.sqlite"

    ok = check_platform_markers("xplat", _BASELINE_XML,
                                directory=str(tmp_path), drift_db=str(db))
    assert ok["status"] == "ok"
    assert drift_events_summary(str(db)) == {}  # событий нет

    drifted = check_platform_markers("xplat", _DRIFTED_XML,
                                     directory=str(tmp_path),
                                     drift_db=str(db))
    assert drifted["status"] == "drift"
    assert drift_events_summary(str(db)) == {"xplat": 1}

    check_platform_markers("xplat", _DRIFTED_XML,
                           directory=str(tmp_path), drift_db=str(db))
    assert drift_events_summary(str(db)) == {"xplat": 2}


def test_marker_check_cli_persists_drift(tmp_path, capsys):
    from aios_cli import main

    _write_descriptor(tmp_path, "xplat", _HINTS)
    dump = tmp_path / "feed.xml"
    dump.write_text(_DRIFTED_XML, encoding="utf-8")
    db = tmp_path / "drift.sqlite"
    import os
    previous = os.getcwd()
    os.chdir(tmp_path)  # descriptor dir = cwd/platforms
    (tmp_path / "platforms").mkdir(exist_ok=True)
    (tmp_path / "platforms" / "xplat.yaml").write_text(
        (tmp_path / "xplat.yaml").read_text(encoding="utf-8"),
        encoding="utf-8")
    try:
        main(["platforms", "marker-check", "--platform", "xplat",
              "--dump", str(dump), "--drift-db", str(db)])
        out = json.loads(capsys.readouterr().out)
        assert out["status"] == "drift"
        assert drift_events_summary(str(db)) == {"xplat": 1}
    finally:
        os.chdir(previous)


def test_telemetry_exposes_drift_series(tmp_path):
    from aios_core.platforms.regression import _record_drift_event
    from aios_core.platforms.telemetry import prometheus_metrics

    db = tmp_path / "drift.sqlite"
    _record_drift_event(str(db), "olx", removed=3)
    _record_drift_event(str(db), "olx", removed=1)
    _record_drift_event(str(db), "tiktok", removed=2)
    text = prometheus_metrics(
        shards_db=str(tmp_path / "s.sqlite"),
        profiles_db=str(tmp_path / "p.sqlite"),
        devices_db=str(tmp_path / "d.sqlite"),
        catalog_dir=str(tmp_path),
        data_dir=str(tmp_path / "empty"),
        drift_db=str(db),
    )
    assert 'aios_marker_drift_events{platform="olx"} 2' in text
    assert 'aios_marker_drift_events{platform="tiktok"} 1' in text


# ---------------------------------------------------------------------------
# K8s operator
# ---------------------------------------------------------------------------

def test_k8s_manifests_valid_and_consistent():
    deploy = Path("deploy/k8s")
    namespace = yaml.safe_load((deploy / "00-namespace.yaml").read_text())
    assert namespace["metadata"]["name"] == "aios-fleet"

    crds = [
        doc for doc in yaml.safe_load_all(
            (deploy / "01-crds.yaml").read_text()) if doc
    ]
    kinds = {crd["spec"]["names"]["kind"] for crd in crds}
    assert kinds == {"Platform", "Profile", "Job"}
    for crd in crds:
        assert crd["spec"]["group"] == "aios.io"
        assert crd["spec"]["versions"][0]["subresources"]["status"] == {}

    rbac = [doc for doc in yaml.safe_load_all(
        (deploy / "02-rbac.yaml").read_text()) if doc]
    role = next(doc for doc in rbac if doc["kind"] == "ClusterRole")
    assert any("aios.io" in rule.get("apiGroups", []) for rule in
               role["rules"])

    deployment_docs = [
        doc for doc in yaml.safe_load_all(
            (deploy / "03-operator-deployment.yaml").read_text()) if doc]
    deployment = next(doc for doc in deployment_docs
                      if doc["kind"] == "Deployment")
    container = deployment["spec"]["template"]["spec"]["containers"][0]
    assert container["image"].startswith("ghcr.io/jotalbot/aios:9.1.0")
    assert "koperator" in container["command"][-1]

    example = [doc for doc in yaml.safe_load_all(
        (deploy / "example-cr.yaml").read_text()) if doc]
    assert [doc["kind"] for doc in example] == [
        "Platform", "Profile", "Job"]


def test_koperator_reconcile_applies_cr(tmp_path):
    from aios_core.platforms.koperator import reconcile
    from aios_core.platforms.store import ProfileStore

    profiles_db = str(tmp_path / "profiles.sqlite")
    shards_db = str(tmp_path / "shards.sqlite")
    objects = [
        {"kind": "Platform", "metadata": {"name": "prom"},
         "spec": {"name": "prom", "androidPackage": "ua.prom.app"}},
        {"kind": "Profile", "metadata": {"name": "work"},
         "spec": {"platformRef": "prom", "name": "work",
                  "deviceSerial": "emulator-5554"}},
        {"kind": "Job", "metadata": {"name": "j1"},
         "spec": {"profileKey": "prom:work", "kind": "reels"}},
        {"kind": "Bogus", "metadata": {"name": "x"}, "spec": {}},
    ]
    report = reconcile(objects, directory=str(tmp_path),
                       profiles_db=profiles_db, shards_db=shards_db)
    assert report["applied"] == {"Platform": 1, "Profile": 1, "Job": 1}
    assert report["errors"] == ["Bogus/x: unknown kind"]

    descriptor = yaml.safe_load((tmp_path / "prom.yaml").read_text())
    assert descriptor["extras"]["compliance"]["autopost_allowed"] is False
    store = ProfileStore(profiles_db)
    assert store.get("prom", "work").device_serial == "emulator-5554"
    store.close()
    from aios_core.platforms.shardexec import ShardJobs
    with ShardJobs(shards_db) as jobs:
        pending = jobs.list(status="pending")
        assert pending[0]["kind"] == "reels"

    # идемпотентность: повторная сверка не падает
    again = reconcile(objects[:2], directory=str(tmp_path),
                      profiles_db=profiles_db, shards_db=shards_db)
    assert again["errors"] == []


def test_koperator_watch_once_uses_injected_opener():
    import json as jsonlib
    from aios_core.platforms.koperator import watch_once_from_api

    class _Response:
        def __init__(self, payload):
            self._payload = payload

        def read(self):
            return jsonlib.dumps(self._payload).encode()

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    seen_urls = []

    def opener(request):
        seen_urls.append(request.full_url)
        plural = request.full_url.rsplit("/", 1)[-1]
        return _Response({"items": [{"kind": plural.title()[:-1],
                                     "metadata": {"name": "x"},
                                     "spec": {}}]})

    objects = watch_once_from_api("https://k8s.local", "aios-fleet",
                                  opener=opener)
    assert len(objects) == 3
    assert any("platforms" in url for url in seen_urls)
    assert any("aios-fleet" in url for url in seen_urls)
