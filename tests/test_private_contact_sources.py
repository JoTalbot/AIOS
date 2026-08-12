import json

from aios_core import google_contacts_sync
from scripts import download_gdrive_audio


def test_contacts_have_no_embedded_fallback(monkeypatch, tmp_path):
    missing = tmp_path / "missing.json"
    monkeypatch.setattr(google_contacts_sync, "CONTACTS_CACHE_FILE", missing)
    assert google_contacts_sync.load_google_contacts() == []
    assert not missing.exists()


def test_audio_folders_are_loaded_from_runtime_manifest(monkeypatch, tmp_path):
    manifest = tmp_path / "folders.json"
    manifest.write_text(json.dumps({"folders": [{"id": "example_folder_id_123", "target": "private-target"}]}))
    monkeypatch.setenv("AIOS_GDRIVE_AUDIO_MANIFEST", str(manifest))
    assert download_gdrive_audio.load_audio_folders() == [("example_folder_id_123", "private-target")]
