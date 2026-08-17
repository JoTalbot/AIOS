"""Hermetic test: Freelancehunt pagination stops on HTTP 400."""

from __future__ import annotations

import json
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aios_core.freelance_brain import FreelanceMarketRadar  # noqa: E402


def _project(item_id: int, title: str) -> dict:
    return {
        "id": item_id,
        "attributes": {
            "name": title,
            "description": f"<p>desc {item_id}</p>",
            "skills": [{"name": "Python"}],
            "budget": {"amount": 1000, "currency": "UAH"},
        },
        "links": {"self": {"web": f"https://freelancehunt.com/project/{item_id}.html"}},
    }


def test_pagination_stops_on_400(monkeypatch, tmp_path):
    calls: list[str] = []

    class FakeResp:
        def __init__(self, payload: dict):
            self._payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self) -> bytes:
            return json.dumps(self._payload).encode()

    def fake_urlopen(req, timeout=10):
        calls.append(req.full_url)
        if "page[number]=2" in req.full_url:
            raise urllib.error.HTTPError(req.full_url, 400, "Bad Request", None, None)
        if "filter[skill_id]" in req.full_url:
            return FakeResp({"data": [_project(1, "Задача Python")]})
        return FakeResp({"data": []})

    monkeypatch.setattr("aios_core.freelance_brain.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("aios_core.freelance_brain.urllib.request.Request",
                        lambda url, headers=None: type("R", (), {"full_url": url})())

    brain = FreelanceMarketRadar(data_dir=str(tmp_path))
    tasks = brain.fetch_freelancehunt_jobs()

    assert len(tasks) == 1
    assert tasks[0].id == "fh_1"
    # страница 1: 2 URL (фильтр + без фильтра); страница 2: 1 URL до 400 и стоп
    assert len(calls) == 3, calls
    assert all("page[number]=3" not in c for c in calls)
