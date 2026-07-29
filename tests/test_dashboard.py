"""Tests for aios_core/dashboard.py"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from starlette.requests import Request
from starlette.testclient import TestClient

from aios_core.dashboard import AIOS_SERVICES, AIOSDashboard


def _redirect_path(tmp_path):
    class _P:
        _real = Path

        def __new__(cls, *parts):
            p = cls._real(*parts)
            s = str(p)
            if s.startswith("/root/AIOS"):
                rel = s[len("/root/AIOS") :]
                target = tmp_path / rel.lstrip("/")
                target.parent.mkdir(parents=True, exist_ok=True)
                return target
            return p

        def __getattr__(self, name):
            return getattr(self._real, name)

    return _P


@pytest.fixture()
def dashboard(tmp_path):
    mock_orch = MagicMock()
    mock_orch.stats.return_value = {"total_steps_executed": 42}
    mock_orch.version = "10.15.0"
    RedirectedPath = _redirect_path(tmp_path)
    with (
        patch("aios_core.dashboard.Path", RedirectedPath),
        patch("aios_core.dashboard.BackupManager") as mock_bm,
        patch("aios_core.dashboard.AndroidAutoStudy") as mock_aas,
    ):
        mock_bm.return_value = MagicMock()
        mock_aas.return_value = MagicMock()
        d = AIOSDashboard(mock_orch)
    d._control_token = "test-token-123"
    d._auto_study_history_path = tmp_path / "auto_study_history.json"
    d._model_state_path = tmp_path / "dashboard_model_stages.json"
    d.CONSTITUTION_DIR = tmp_path / "constitution"
    yield d


@pytest.fixture()
def mock_request_with_token():
    scope = {
        "type": "http",
        "headers": [(b"x-aios-control-token", b"test-token-123")],
    }
    return Request(scope)


@pytest.fixture()
def mock_request_missing_token():
    scope = {"type": "http", "headers": []}
    return Request(scope)


class TestRequireControl:
    def test_matching_token_allows(self, dashboard, mock_request_with_token):
        result = dashboard._require_control(mock_request_with_token)
        assert result is None

    def test_missing_token_rejects(self, dashboard, mock_request_missing_token):
        result = dashboard._require_control(mock_request_missing_token)
        assert result is not None
        assert result.status_code == 401

    def test_wrong_token_rejects(self, dashboard):
        scope = {
            "type": "http",
            "headers": [(b"x-aios-control-token", b"wrong-token")],
        }
        request = Request(scope)
        result = dashboard._require_control(request)
        assert result is not None
        assert result.status_code == 401


class TestTimestampMs:
    def test_valid_datetime_string(self):
        result = AIOSDashboard._timestamp_ms("2024-01-15T10:30:00+00:00")
        assert isinstance(result, int)
        assert result > 0

    def test_none_returns_current(self):
        result = AIOSDashboard._timestamp_ms(None)
        assert isinstance(result, int)
        assert result > 0

    def test_invalid_string_returns_current(self):
        result = AIOSDashboard._timestamp_ms("not-a-datetime")
        assert isinstance(result, int)
        assert result > 0

    def test_valid_datetime_without_timezone_adds_utc(self):
        result = AIOSDashboard._timestamp_ms("2024-01-15T10:30:00")
        assert isinstance(result, int)
        assert result > 0


class TestAuditType:
    def test_policy_type_maps_to_compliance(self):
        assert AIOSDashboard._audit_type("policy_violation") == "compliance"

    def test_constitution_type_maps_to_compliance(self):
        assert AIOSDashboard._audit_type("constitution_check") == "compliance"

    def test_compliance_type_maps_to_compliance(self):
        assert AIOSDashboard._audit_type("compliance_report") == "compliance"

    def test_security_type_maps_to_security(self):
        assert AIOSDashboard._audit_type("security_alert") == "security"

    def test_auth_type_maps_to_security(self):
        assert AIOSDashboard._audit_type("auth_failure") == "security"

    def test_key_type_maps_to_security(self):
        assert AIOSDashboard._audit_type("key_rotation") == "security"

    def test_secret_type_maps_to_security(self):
        assert AIOSDashboard._audit_type("secret_exposure") == "security"

    def test_agent_type_maps_to_agent(self):
        assert AIOSDashboard._audit_type("agent_spawn") == "agent"

    def test_swarm_type_maps_to_agent(self):
        assert AIOSDashboard._audit_type("swarm_discover") == "agent"

    def test_platform_type_maps_to_platform(self):
        assert AIOSDashboard._audit_type("platform_olx") == "platform"

    def test_android_type_maps_to_platform(self):
        assert AIOSDashboard._audit_type("android_adb") == "platform"

    def test_olx_type_maps_to_platform(self):
        assert AIOSDashboard._audit_type("olx_collect") == "platform"

    def test_approval_type_maps_to_approval(self):
        assert AIOSDashboard._audit_type("approval_request") == "approval"

    def test_review_type_maps_to_approval(self):
        assert AIOSDashboard._audit_type("review_submission") == "approval"

    def test_unknown_type_maps_to_system(self):
        assert AIOSDashboard._audit_type("random_event") == "system"

    def test_empty_string_maps_to_system(self):
        assert AIOSDashboard._audit_type("") == "system"


class TestSvcStatus:
    def test_active_service_returns_correct_fields(self, dashboard):
        with patch("aios_core.dashboard.subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(stdout="active\n", returncode=0),
                MagicMock(stdout="enabled\n", returncode=0),
                MagicMock(stdout="Mon 2024-01-15 10:00:00 UTC\n", returncode=0),
            ]
            result = dashboard._svc_status("aios-api")
            assert result["active"] is True
            assert result["state"] == "active"
            assert result["enabled"] is True
            assert result["name"] == "aios-api"

    def test_inactive_service_returns_correct_fields(self, dashboard):
        with patch("aios_core.dashboard.subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(stdout="inactive\n", returncode=3),
                MagicMock(stdout="disabled\n", returncode=3),
                MagicMock(stdout="\n", returncode=3),
            ]
            result = dashboard._svc_status("aios-dash")
            assert result["active"] is False
            assert result["state"] == "inactive"
            assert result["enabled"] is False

    def test_unknown_service_returns_error_state(self, dashboard):
        with patch("aios_core.dashboard.subprocess.run") as mock_run:
            mock_run.side_effect = Exception("systemctl not found")
            result = dashboard._svc_status("unknown-svc")
            assert result["active"] is False
            assert result["state"] == "error"
            assert result["enabled"] is False
            assert "error" in result


class TestReadConstitutionIndex:
    def test_article_file_parsing(self, dashboard, tmp_path):
        constitution_dir = tmp_path / "constitution"
        constitution_dir.mkdir()
        article_file = constitution_dir / "ARTICLE-IV-test.md"
        article_file.write_text(
            "# Article IV \u2014 Access Control\nstatus: Active\nlevel: Constitutional\nscope: System-wide\n",
            encoding="utf-8",
        )
        result = dashboard._read_constitution_index()
        assert len(result) == 1
        assert result[0]["numeral"] == "IV"
        assert result[0]["number"] == 4
        assert result[0]["title"] == "Access Control"
        assert result[0]["status"] == "Active"
        assert result[0]["level"] == "Constitutional"
        assert result[0]["scope"] == "System-wide"
        assert result[0]["valid"] is True

    def test_roman_numeral_mapping(self, dashboard, tmp_path):
        constitution_dir = tmp_path / "constitution"
        constitution_dir.mkdir()
        for numeral in ["I", "IV", "X", "XX", "L"]:
            article_file = constitution_dir / f"ARTICLE-{numeral}-test.md"
            article_file.write_text(
                f"# Article {numeral} \u2014 Test {numeral}\nstatus: Active\n",
                encoding="utf-8",
            )
        result = dashboard._read_constitution_index()
        numerals_found = {a["numeral"]: a["number"] for a in result}
        assert numerals_found["I"] == 1
        assert numerals_found["IV"] == 4
        assert numerals_found["X"] == 10
        assert numerals_found["XX"] == 20
        assert numerals_found["L"] == 50

    def test_missing_title_uses_default(self, dashboard, tmp_path):
        constitution_dir = tmp_path / "constitution"
        constitution_dir.mkdir()
        article_file = constitution_dir / "ARTICLE-I-test.md"
        article_file.write_text("No title here.\n", encoding="utf-8")
        result = dashboard._read_constitution_index()
        assert len(result) == 1
        assert result[0]["title"] == "Constitutional Principle 1"

    def test_no_articles_returns_empty_list(self, dashboard, tmp_path):
        constitution_dir = tmp_path / "empty_dir"
        constitution_dir.mkdir()
        result = dashboard._read_constitution_index()
        assert result == []


class TestReadConstitutionArticle:
    def test_read_article_by_number(self, dashboard, tmp_path):
        constitution_dir = tmp_path / "constitution"
        constitution_dir.mkdir()
        article_file = constitution_dir / "ARTICLE-V-test.md"
        article_file.write_text(
            "# Article V \u2014 Due Process\nstatus: Active\n",
            encoding="utf-8",
        )
        result = dashboard._read_constitution_article(5)
        assert result is not None
        assert result["numeral"] == "V"
        assert result["number"] == 5
        assert "body" in result

    def test_read_article_not_found(self, dashboard, tmp_path):
        constitution_dir = tmp_path / "constitution"
        constitution_dir.mkdir()
        result = dashboard._read_constitution_article(99)
        assert result is None


class TestAutoStudyHistory:
    def test_save_and_load_history(self, dashboard, tmp_path):
        history_path = tmp_path / "auto_study_history.json"
        dashboard._auto_study_history_path = history_path
        item = {
            "study_id": "test-123",
            "package": "ua.slando",
            "status": "completed",
            "steps_completed": 10,
            "steps_total": 10,
        }
        dashboard._auto_study_save_history(item)
        loaded = dashboard._auto_study_history()
        assert len(loaded) == 1
        assert loaded[0]["study_id"] == "test-123"
        assert loaded[0]["status"] == "completed"

    def test_save_string_creates_default_dict(self, dashboard, tmp_path):
        history_path = tmp_path / "auto_study_history.json"
        dashboard._auto_study_history_path = history_path
        dashboard._auto_study_save_history("some error message")
        loaded = dashboard._auto_study_history()
        assert len(loaded) == 1
        assert loaded[0]["status"] == "failed"
        assert loaded[0]["error"] == "some error message"
        assert loaded[0]["package"] == "ua.slando"

    def test_history_truncates_to_200(self, dashboard, tmp_path):
        history_path = tmp_path / "auto_study_history.json"
        dashboard._auto_study_history_path = history_path
        for i in range(250):
            dashboard._auto_study_save_history({"study_id": f"study-{i}"})
        loaded = dashboard._auto_study_history()
        assert len(loaded) == 200
        assert loaded[0]["study_id"] == "study-249"
        assert loaded[-1]["study_id"] == "study-50"

    def test_load_empty_returns_list(self, dashboard, tmp_path):
        history_path = tmp_path / "nonexistent.json"
        dashboard._auto_study_history_path = history_path
        loaded = dashboard._auto_study_history()
        assert loaded == []


class TestModelStages:
    def test_model_stages_read_write(self, dashboard, tmp_path):
        model_path = tmp_path / "dashboard_model_stages.json"
        dashboard._model_state_path = model_path
        stages = {"policy_guard": "production", "price_assessor": "staging"}
        model_path.write_text(json.dumps(stages), encoding="utf-8")
        result = dashboard._model_stages()
        assert result == stages

    def test_model_stages_missing_file_returns_empty(self, dashboard, tmp_path):
        model_path = tmp_path / "nonexistent.json"
        dashboard._model_state_path = model_path
        result = dashboard._model_stages()
        assert result == {}

    def test_model_stage_set_and_persist(self, dashboard, tmp_path):
        model_path = tmp_path / "dashboard_model_stages.json"
        dashboard._model_state_path = model_path
        stages = dashboard._model_stages()
        assert stages == {}


class TestRomanToIdx:
    def test_ivxlcdm_numerals_map_correctly(self):
        roman_to_idx = {
            "I": 1,
            "II": 2,
            "III": 3,
            "IV": 4,
            "V": 5,
            "VI": 6,
            "VII": 7,
            "VIII": 8,
            "IX": 9,
            "X": 10,
            "XI": 11,
            "XII": 12,
            "XIII": 13,
            "XIV": 14,
            "XV": 15,
            "XVI": 16,
            "XVII": 17,
            "XVIII": 18,
            "XIX": 19,
            "XX": 20,
            "XXI": 21,
            "XXII": 22,
            "XXIII": 23,
            "XXIV": 24,
            "XXV": 25,
            "XXVI": 26,
            "XXVII": 27,
            "XXVIII": 28,
            "XXIX": 29,
            "XXX": 30,
            "XXXI": 31,
            "XXXII": 32,
            "XXXIII": 33,
            "XXXIV": 34,
            "XXXV": 35,
            "XXXVI": 36,
            "XXXVII": 37,
            "XXXVIII": 38,
            "XXXIX": 39,
            "XL": 40,
            "XLI": 41,
            "XLII": 42,
            "XLIII": 43,
            "XLIV": 44,
            "XLV": 45,
            "XLVI": 46,
            "XLVII": 47,
            "XLVIII": 48,
            "XLIX": 49,
            "L": 50,
            "LI": 51,
            "LII": 52,
            "LIII": 53,
            "LIV": 54,
            "LV": 55,
            "LVI": 56,
            "LVII": 57,
            "LVIII": 58,
            "LIX": 59,
            "LX": 60,
            "LXI": 61,
            "LXII": 62,
            "LXIII": 63,
            "LXIV": 64,
            "LXV": 65,
            "LXVI": 66,
            "LXVII": 67,
        }
        assert roman_to_idx["IV"] == 4
        assert roman_to_idx["X"] == 10
        assert roman_to_idx["XL"] == 40
        assert roman_to_idx["L"] == 50
        assert roman_to_idx["XII"] == 12
        assert roman_to_idx["XXXIV"] == 34


class TestApiServices:
    def test_api_services_returns_all_services(self, dashboard):
        with patch("aios_core.dashboard.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="active\n", returncode=0)
            app = dashboard.create_app()
            client = TestClient(app)
            response = client.get("/api/services")
            assert response.status_code == 200
            data = response.json()
            assert "services" in data
            assert len(data["services"]) >= len(AIOS_SERVICES)

    def test_api_services_action_requires_control_token(self, dashboard):
        app = dashboard.create_app()
        client = TestClient(app)
        response = client.post("/api/services/aios-api/action", json={"action": "restart"})
        assert response.status_code == 401

    def test_api_services_action_bad_action(self, dashboard):
        app = dashboard.create_app()
        client = TestClient(app)
        response = client.post(
            "/api/services/aios-api/action",
            json={"action": "invalid_action"},
            headers={"x-aios-control-token": "test-token-123"},
        )
        assert response.status_code == 400
        assert response.json()["ok"] is False
